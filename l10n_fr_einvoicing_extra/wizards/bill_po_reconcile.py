import itertools
import logging
import re

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

from odoo.addons.project_accounting.models.project_outsourcing_link import OUTSOURCING_LINK_TYPES

logger = logging.getLogger(__name__)

# Au-delà, on renonce à la recherche exhaustive de sous-ensembles (2^n combinaisons).
MAX_SUBSET_LINES = 16

BILLING_STATES = [
    ("open", "Ouverte"),
    ("partial", "Partiellement facturée"),
    ("full", "Facturée"),
    ("direct", "Facturation directe"),
]


def _analytic_accounts(distribution):
    """{'12,13': 50, '14': 50} -> {12, 13, 14}"""
    accounts = set()
    for key in (distribution or {}):
        accounts.update(int(k) for k in str(key).split(",") if k)
    return accounts


class BillPoReconcileWizard(models.TransientModel):
    _name = "bill.po.reconcile.wizard"
    _description = "Rapprochement facture fournisseur / bon de commande"

    move_id = fields.Many2one("account.move", required=True, readonly=True, ondelete="cascade")
    currency_id = fields.Many2one(related="move_id.currency_id")
    partner_id = fields.Many2one(related="move_id.partner_id", string="Fournisseur")
    project_ids = fields.Many2many("project.project", string="Projets")
    allowed_order_ids = fields.Many2many("purchase.order", compute="_compute_allowed_order_ids")
    order_ids = fields.Many2many("purchase.order", string="BC sélectionné(s)")
    new_order = fields.Boolean("BC à créer")
    allowed_envelope_line_ids = fields.Many2many(
        "purchase.order.line", compute="_compute_allowed_envelope_line_ids", string="Enveloppes disponibles"
    )
    envelope_line_id = fields.Many2one(
        "purchase.order.line",
        string="Consommer l'enveloppe « frais divers »",
        help="Ligne du BC du fournisseur « frais divers » pour ce projet, diminuée du montant rapproché.",
    )
    envelope_message = fields.Char(compute="_compute_summary")
    needs_link_type = fields.Boolean(compute="_compute_needs_link_type")
    link_type = fields.Selection(
        OUTSOURCING_LINK_TYPES,
        string="Type d'achat",
        default="other",
        help="Type du lien projet / fournisseur à créer (le fournisseur de la facture n'est pas encore déclaré sur le projet).",
    )
    mode = fields.Selection(
        [("consumption", "Consommation"), ("replacement", "Remplacement")], default="replacement", required=True
    )
    suggestion_ids = fields.One2many("bill.po.reconcile.suggestion", "wizard_id", string="Suggestions")
    invoice_line_ids = fields.One2many("bill.po.reconcile.invoice.line", "wizard_id", string="Lignes de la facture")
    po_line_ids = fields.One2many("bill.po.reconcile.po.line", "wizard_id", string="Lignes de BC")

    invoice_total = fields.Monetary(compute="_compute_summary", currency_field="currency_id")
    po_total = fields.Monetary(compute="_compute_summary", currency_field="currency_id")
    message = fields.Char(compute="_compute_summary")
    is_valid = fields.Boolean(compute="_compute_summary")
    button_key = fields.Selection(
        [
            ("create", "Créer le BC"),
            ("replace", "Remplacer & rattacher"),
            ("split", "Scinder & rattacher"),
            ("associate", "Associer"),
            ("attach", "Rattacher"),
        ],
        compute="_compute_summary",
    )

    # ------------------------------------------------------------------
    # Ouverture et construction des lignes
    # ------------------------------------------------------------------
    @api.depends("new_order", "project_ids", "move_id.partner_id")
    def _compute_needs_link_type(self):
        """Le type d'achat se choisit seulement quand le BC à créer impose de créer le lien projet / fournisseur."""
        link = self.env["project.outsourcing.link"]
        for wiz in self:
            wiz.needs_link_type = bool(
                wiz.new_order
                and len(wiz.project_ids) == 1
                and wiz.move_id.partner_id
                and not link.search_count(
                    [("project_id", "=", wiz.project_ids.id), ("partner_id", "=", wiz.move_id.partner_id.id)]
                )
            )

    @api.depends("project_ids", "link_type", "move_id.partner_id", "move_id.company_id.expense_envelope_partner_id")
    def _compute_allowed_envelope_line_ids(self):
        """Lignes des BC du fournisseur « frais divers » (réglage société) pour le projet, encore à consommer.
        Proposées seulement si le fournisseur de la facture est du type « Autres / Hors prestation intellectuelle »."""
        for wiz in self:
            lines = self.env["purchase.order.line"]
            envelope_partner = wiz.move_id.company_id.expense_envelope_partner_id
            if (
                envelope_partner
                and len(wiz.project_ids) == 1
                and wiz.move_id.commercial_partner_id != envelope_partner.commercial_partner_id
                and wiz._supplier_link_type() == "other"
            ):
                lines = (
                    self.env["purchase.order.line"]
                    .search(
                        [
                            ("order_id.partner_id.commercial_partner_id", "=", envelope_partner.commercial_partner_id.id),
                            ("order_id.state", "=", "purchase"),
                            ("company_id", "=", wiz.move_id.company_id.id),
                            ("rel_project_ids", "in", wiz.project_ids.ids),
                        ]
                    )
                    .filtered(
                        lambda l: not l.display_type
                        and l.price_subtotal > 0
                        and l.order_id.amount_untaxed > 0  # net des lignes « Consommé par… » déjà posées
                        and not l.consumed_by_move_id  # pas une ligne de trace
                    )
                )
            wiz.allowed_envelope_line_ids = lines

    # ------------------------------------------------------------------
    # Facture sans projet : suggestions de projet / BC
    # ------------------------------------------------------------------
    def _build_suggestions(self):
        """Quand le projet n'est pas connu, propose les couples (projet, BC) du fournisseur ayant un reste à
        facturer, classés par pertinence. Un seul projet possible : il est présélectionné, sans liste."""
        self.ensure_one()
        move = self.move_id
        Suggestion = self.env["bill.po.reconcile.suggestion"]
        self.suggestion_ids = [Command.clear()]
        if not move.commercial_partner_id:
            return
        rounding = move.currency_id.rounding or 0.01
        orders = self.env["purchase.order"].search(
            [
                ("partner_id.commercial_partner_id", "=", move.commercial_partner_id.id),
                ("state", "=", "purchase"),
                ("company_id", "=", move.company_id.id),
            ]
        )
        pols = orders.order_line.filtered(lambda l: not l.display_type)
        infos = self._pol_infos(pols)
        unlinked = move.invoice_line_ids.filtered(lambda l: l.display_type == "product" and not l.purchase_line_id)
        target = sum(unlinked.mapped("price_subtotal"))
        invoice_products = unlinked.product_id
        text = " ".join(
            filter(None, [move.ref, move.invoice_origin, re.sub(r"<[^>]+>", " ", move.narration or "")])
        ).lower()
        last_projects = self._last_projects_of_supplier()
        # (projet, BC) -> reste à facturer des lignes ouvertes du BC rattachées à ce projet
        pairs = {}
        for pol in pols:
            if infos[pol.id]["state"] not in ("open", "partial") or infos[pol.id]["amount_open"] <= 0:
                continue
            for project in pol.rel_project_ids:
                pairs.setdefault((project.id, pol.order_id.id), self.env["purchase.order.line"])
                pairs[(project.id, pol.order_id.id)] |= pol
        by_project = {}
        for (project_id, order_id), lines in pairs.items():
            by_project.setdefault(project_id, {})[order_id] = sum(infos[l.id]["amount_open"] for l in lines)
        if not by_project:
            return
        if len(by_project) == 1:  # un seul projet possible : présélectionné, pas de liste
            project = self.env["project.project"].browse(next(iter(by_project)))
            self.project_ids = project
            self.order_ids = self.env["purchase.order"].browse(list(by_project[project.id]))
            self._apply_default_mode()
            self._rebuild_lines()
            return
        order_rec = self.env["purchase.order"]
        vals_list = []
        for project_id, order_amounts in by_project.items():
            combo = ()
            if target:
                found = self._find_subsets(list(order_amounts.items()), target, rounding, limit=1)
                combo = found[0] if found and len(found[0]) > 1 else ()
            for order_id, amount in order_amounts.items():
                order = order_rec.browse(order_id)
                lines = pairs[(project_id, order_id)]
                reasons, score, selected = [], 0, False
                if text and order.name.lower() in text:
                    reasons.append("nom du BC dans la référence")
                    score += 60
                    selected = True
                if target and float_compare(amount, target, precision_rounding=rounding) == 0:
                    reasons.append("montant identique")
                    score += 50
                    selected = True
                elif order_id in combo:
                    reasons.append("combinaison des BC cochés = %.2f" % target)
                    score += 40
                    selected = True
                if invoice_products and (lines.product_id & invoice_products):
                    reasons.append("même produit")
                    score += 15
                dates = [d for d in lines.mapped("previsional_invoice_date") if d]
                if move.invoice_date and any(abs((d - move.invoice_date).days) <= 30 for d in dates):
                    reasons.append("date de facturation prévue proche")
                    score += 10
                if project_id in last_projects:
                    reasons.append("dernier projet utilisé")
                    score += 5
                vals_list.append(
                    {
                        "wizard_id": self.id,
                        "project_id": project_id,
                        "order_id": order_id,
                        "amount_open": amount,
                        "reasons": ", ".join(reasons),
                        "score": score,
                        "selected": selected,
                    }
                )
        vals_list.sort(key=lambda v: -v["score"])
        for sequence, vals in enumerate(vals_list):
            vals["sequence"] = sequence
        Suggestion.create(vals_list)

    def _last_projects_of_supplier(self):
        """Projets de la dernière facture fournisseur qui en porte, pour ce fournisseur."""
        self.ensure_one()
        last = self.env["account.move"].search(
            [
                ("move_type", "=", "in_invoice"),
                ("commercial_partner_id", "=", self.move_id.commercial_partner_id.id),
                ("id", "!=", self.move_id.id),
                ("state", "!=", "cancel"),
            ],
            order="invoice_date desc, id desc",
            limit=10,
        )
        for move in last:
            if move.rel_project_ids:
                return set(move.rel_project_ids.ids)
        return set()

    def action_apply_suggestions(self):
        self.ensure_one()
        checked = self.suggestion_ids.filtered("selected")
        if not checked:
            raise UserError("Cochez au moins un BC dans la liste des suggestions.")
        if len(checked.project_id) > 1:
            raise UserError("Cochez des BC d'un seul projet (plusieurs BC sont possibles s'ils sont sur le même projet).")
        self.project_ids = checked.project_id
        self.order_ids = checked.order_id
        self.new_order = False
        self._apply_default_mode()
        self._rebuild_lines()
        self.envelope_line_id = False
        self._apply_envelope_default()
        return self._reopen()

    def _supplier_link_type(self):
        """Type d'achat du fournisseur de la facture sur le projet : lien existant, sinon choix du wizard."""
        self.ensure_one()
        link = self.env["project.outsourcing.link"].search(
            [("project_id", "=", self.project_ids[:1].id), ("partner_id", "=", self.move_id.partner_id.id)], limit=1
        )
        return link.link_type if link else self.link_type

    def _apply_envelope_default(self):
        """Les enveloppes ne sont proposées que pour un fournisseur de type « autres » ; la première est
        présélectionnée, l'utilisateur peut en choisir une autre ou n'en consommer aucune."""
        for wiz in self:
            lines = wiz.allowed_envelope_line_ids
            if wiz.envelope_line_id and wiz.envelope_line_id in lines:
                continue
            wiz.envelope_line_id = lines[:1]

    @api.onchange("link_type")
    def _onchange_link_type(self):
        self.envelope_line_id = False
        self._apply_envelope_default()

    @api.depends("move_id", "project_ids")
    def _compute_allowed_order_ids(self):
        for wiz in self:
            wiz.allowed_order_ids = wiz._get_allowed_orders()

    def _get_allowed_orders(self):
        self.ensure_one()
        if not self.move_id.commercial_partner_id:
            return self.env["purchase.order"]
        orders = self.env["purchase.order"].search(
            [
                ("partner_id.commercial_partner_id", "=", self.move_id.commercial_partner_id.id),
                ("state", "in", ("purchase", "done")),
                ("company_id", "=", self.move_id.company_id.id),
            ]
        )
        if self.project_ids:
            # rel_project_ids de la ligne (stocké) et non celui du BC (calculé sans dépendances déclarées)
            orders = orders.filtered(lambda o: o.order_line.rel_project_ids & self.project_ids)
        return orders

    @api.onchange("project_ids")
    def _onchange_project_ids(self):
        self.order_ids = self._get_allowed_orders() if self.project_ids else False
        self.new_order = False
        self._apply_default_mode()
        self._rebuild_lines()
        self.envelope_line_id = False
        self._apply_envelope_default()

    @api.onchange("order_ids", "new_order")
    def _onchange_order_ids(self):
        self._apply_default_mode()
        self._rebuild_lines()
        self._apply_envelope_default()

    def _apply_default_mode(self):
        """Règle 3 : consommation dès qu'une ligne non entièrement facturée a une quantité > 1."""
        for wiz in self:
            lines = wiz.order_ids.order_line.filtered(lambda l: not l.display_type)
            infos = wiz._pol_infos(lines)
            wiz.mode = (
                "consumption"
                if any(l.product_qty > 1 and infos[l.id]["state"] in ("open", "partial") for l in lines)
                else "replacement"
            )

    def _pol_infos(self, pols):
        """État de facturation de chaque ligne de BC, calculé ici (objet temporaire) et non persisté."""
        rounding = self.move_id.currency_id.rounding or 0.01
        mirror_ids = set()
        if pols and "auto_purchase_line_id" in self.env["sale.order.line"]._fields:
            # sudo : les règles d'accès cachent ces lignes de vente aux utilisateurs courants
            mirror_ids = {
                d["auto_purchase_line_id"][0]
                for d in self.env["sale.order.line"]
                .sudo()
                .search_read([("auto_purchase_line_id", "in", pols.ids)], ["auto_purchase_line_id"])
            }
        infos = {}
        for pol in pols:
            invoiced = 0.0
            for inv_line in pol.invoice_lines:
                if inv_line.move_id.state == "cancel":
                    continue
                sign = -1.0 if inv_line.move_id.move_type in ("in_refund", "out_refund") else 1.0
                invoiced += sign * inv_line.price_subtotal
            subtotal = pol.price_subtotal
            amount_open = subtotal - invoiced
            qty_open = max(pol.product_qty - pol.qty_invoiced, 0.0)
            if pol.direct_payment_sale_order_line_id:
                state = "direct"
            elif pol.qty_invoiced_override and any(l.move_id.state != "cancel" for l in pol.invoice_lines):
                state = "full"
            elif not float_is_zero(invoiced, precision_rounding=rounding):
                state = "full" if float_compare(amount_open, 0.0, precision_rounding=rounding) <= 0 else "partial"
            elif pol.product_qty and float_is_zero(qty_open, precision_digits=4):
                state = "full"
            else:
                state = "open"
            infos[pol.id] = {
                "state": state,
                "amount_invoiced": invoiced,
                "amount_open": max(amount_open, 0.0) if state in ("open", "partial") else 0.0,
                "qty_open": qty_open,
                "is_mirror": pol.id in mirror_ids,
            }
        return infos

    def _rebuild_lines(self):
        self.ensure_one()
        move = self.move_id
        inv_cmds = [Command.clear()]
        analytic_accounts = set()
        unlinked = self.env["account.move.line"]
        for aml in move.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            linked = bool(aml.purchase_line_id)
            if not linked:
                unlinked |= aml
                analytic_accounts |= _analytic_accounts(aml.analytic_distribution)
            inv_cmds.append(
                Command.create(
                    {
                        "move_line_id": aml.id,
                        "name": aml.name,
                        "quantity": aml.quantity,
                        "price_unit": aml.price_unit,
                        "price_subtotal": aml.price_subtotal,
                        "linked": linked,
                        "selected": not linked,
                    }
                )
            )
        po_cmds = [Command.clear()]
        candidates = []
        pols = self.order_ids.order_line.filtered(lambda l: not l.display_type)
        infos = self._pol_infos(pols)
        for order in self.order_ids:
            order_pols = order.order_line.filtered(lambda l: not l.display_type)
            # BC multi-projets : seules les lignes de même code analytique que la facture sont candidates
            multi_projects = len({tuple(sorted(_analytic_accounts(l.analytic_distribution))) for l in order_pols}) > 1
            for pol in order_pols:
                info = infos[pol.id]
                analytic_ok = True
                if multi_projects and analytic_accounts:
                    analytic_ok = bool(_analytic_accounts(pol.analytic_distribution) & analytic_accounts)
                selectable = info["state"] in ("open", "partial") and analytic_ok
                vals = {
                    "purchase_line_id": pol.id,
                    "order_id": order.id,
                    "name": pol.name,
                    "product_qty": pol.product_qty,
                    "price_unit": pol.price_unit,
                    "price_subtotal": pol.price_subtotal,
                    "state": info["state"],
                    "amount_invoiced": info["amount_invoiced"],
                    "amount_open": info["amount_open"],
                    "qty_open": info["qty_open"],
                    "qty_consumed": info["qty_open"],
                    "is_mirror": info["is_mirror"],
                    "analytic_ok": analytic_ok,
                    "selectable": selectable,
                    "selected": False,
                }
                candidates.append(vals)
                po_cmds.append(Command.create(vals))
        # Présélection automatique par montant : seulement si la combinaison est unique
        if self.mode == "replacement" and not self.new_order and unlinked:
            target = sum(unlinked.mapped("price_subtotal"))
            pool = [
                (i, v["amount_open"])
                for i, v in enumerate(candidates)
                if v["selectable"] and not v["is_mirror"] and v["amount_open"] > 0
            ]
            found = self._find_subsets(pool, target, move.currency_id.rounding or 0.01, limit=2)
            if len(found) == 1:
                for idx in found[0]:
                    po_cmds[idx + 1][2]["selected"] = True
        self.invoice_line_ids = inv_cmds
        self.po_line_ids = po_cmds

    @api.model
    def _find_subsets(self, items, target, rounding, limit=2):
        """items = [(clé, montant)] -> jusqu'à `limit` tuples de clés dont la somme égale `target`."""
        if len(items) > MAX_SUBSET_LINES:
            return []
        found = []
        for size in range(1, len(items) + 1):
            for combo in itertools.combinations(items, size):
                if float_compare(sum(a for _k, a in combo), target, precision_rounding=rounding) == 0:
                    found.append(tuple(k for k, _a in combo))
                    if len(found) >= limit:
                        return found
        return found

    # ------------------------------------------------------------------
    # Résumé et validation (calculés en direct dans le formulaire)
    # ------------------------------------------------------------------
    @api.depends(
        "mode",
        "new_order",
        "project_ids",
        "invoice_line_ids.selected",
        "invoice_line_ids.price_subtotal",
        "po_line_ids.selected",
        "po_line_ids.amount_open",
        "po_line_ids.qty_consumed",
        "envelope_line_id",
    )
    def _compute_summary(self):
        for wiz in self:
            inv = wiz.invoice_line_ids.filtered("selected")
            pols = wiz.po_line_ids.filtered("selected")
            wiz.invoice_total = sum(inv.mapped("price_subtotal"))
            wiz.po_total = sum(pols.mapped("amount_open"))
            msg = wiz._validation_message()
            wiz.message = msg or "Prêt."
            wiz.is_valid = not msg
            wiz.button_key = wiz._compute_button_key()
            wiz.envelope_message = wiz._envelope_message()

    def _envelope_amounts(self):
        """(montant retiré de l'enveloppe, dépassement, montant de la ligne d'enveloppe)."""
        self.ensure_one()
        line = self.envelope_line_id
        if not line:
            return 0.0, 0.0, 0.0
        invoiced = sum(self.invoice_line_ids.filtered("selected").mapped("price_subtotal"))
        total = line.order_id.amount_untaxed  # reste net de l'enveloppe (BC)
        deducted = min(invoiced, total)
        return deducted, max(invoiced - deducted, 0.0), total

    def _envelope_message(self):
        self.ensure_one()
        if not self.envelope_line_id:
            return False
        deducted, overrun, total = self._envelope_amounts()
        msg = "Enveloppe « frais divers » : %.2f → %.2f." % (total, total - deducted)
        if overrun:
            msg += " Dépassement de %.2f : l'enveloppe est ramenée à 0 et une ligne positive « Dépassement » l'enregistre dans son BC." % overrun
        order = self.envelope_line_id.order_id
        if float_compare(order.amount_untaxed - deducted, 0.0, precision_rounding=self.move_id.currency_id.rounding or 0.01) <= 0:
            msg += " Son BC sera annulé."
        return msg

    def _compute_button_key(self):
        self.ensure_one()
        pols = self.po_line_ids.filtered("selected")
        if self.new_order and not pols:
            return "create"
        if not pols:
            return "attach"
        if all(pols.mapped("is_mirror")):
            return "attach"
        if self.mode == "consumption":
            if all(float_compare(p.qty_consumed, p.qty_open, precision_digits=4) == 0 for p in pols):
                return "attach"
            return "split"
        has_partial = any(p.state == "partial" for p in pols)
        has_normal = any(p.state != "partial" for p in pols)
        if has_partial and has_normal:
            return "associate"
        return "split" if has_partial else "replace"

    def _validation_message(self):
        self.ensure_one()
        rounding = self.move_id.currency_id.rounding or 0.01
        inv = self.invoice_line_ids.filtered("selected")
        pols = self.po_line_ids.filtered("selected")
        if not self.project_ids:
            return "Saisissez d'abord le projet."
        if self.envelope_line_id:
            if self.envelope_line_id not in self.allowed_envelope_line_ids:
                return "La ligne d'enveloppe « frais divers » choisie n'est pas disponible pour ce projet."
            if self.envelope_line_id.order_id.currency_id != self.move_id.currency_id:
                return "La devise de l'enveloppe diffère de celle de la facture."
        if not inv:
            return "Cochez au moins une ligne de la facture."
        if self.new_order:
            if pols:
                return "Un BC à créer se traite seul : décochez les lignes de BC existantes."
            if len(self.project_ids) != 1:
                return "Un nouveau BC se crée pour un seul projet."
            return ""
        if not pols:
            return "Cochez au moins une ligne de BC (ou créez un nouveau BC)."
        if any(not p.selectable for p in pols):
            return "Une des lignes de BC cochées n'est pas sélectionnable."
        if any(p.order_id.currency_id != self.move_id.currency_id for p in pols):
            return "La devise du BC diffère de celle de la facture."
        mirrors = pols.filtered("is_mirror")
        if mirrors and mirrors != pols:
            return "Une ligne de BC inter-société ne se rattache pas avec d'autres lignes : traitez-la séparément."
        if mirrors:
            if len(pols) > 1 and len(inv) != len(pols):
                return "Rattachement inter-société : cochez autant de lignes de facture que de lignes de BC."
            return ""
        if self.mode == "consumption":
            for p in pols:
                if float_compare(p.qty_consumed, 0.0, precision_digits=4) <= 0:
                    return "La quantité consommée doit être positive."
                if float_compare(p.qty_consumed, p.qty_open, precision_digits=4) > 0:
                    return "La quantité consommée dépasse le reste à facturer (%s)." % p.qty_open
            if len(pols) > 1 and len(inv) != len(pols):
                return "En consommation, cochez une ligne de facture par ligne de BC."
            return ""
        total_inv = sum(inv.mapped("price_subtotal"))
        total_po = sum(pols.mapped("amount_open"))
        if float_compare(total_inv, total_po, precision_rounding=rounding) != 0:
            return "Écart entre la facture (%.2f) et les lignes de BC (%.2f)." % (total_inv, total_po)
        return ""

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": {"dialog_size": "extra-large"},
        }

    def action_new_order(self):
        self.ensure_one()
        self.new_order = True
        self._onchange_order_ids()
        return self._reopen()

    def action_cancel_new_order(self):
        self.ensure_one()
        self.new_order = False
        self._onchange_order_ids()
        return self._reopen()

    def action_associate(self):
        """Une validation = une transaction : en cas d'erreur, rien n'est écrit (tous les BC ou aucun)."""
        self.ensure_one()
        msg = self._validation_message()
        if msg:
            raise UserError(msg)
        inv_amls = self.invoice_line_ids.filtered("selected").mapped("move_line_id")
        wpols = self.po_line_ids.filtered("selected")
        if self.new_order and not wpols:
            touched = self._do_create_order(inv_amls)
        elif all(wpols.mapped("is_mirror")):
            touched = self._do_attach_only(inv_amls, wpols)
        elif self.mode == "consumption":
            touched = self._do_consumption(inv_amls, wpols)
        else:
            touched = self._do_replacement(inv_amls, wpols)
        if self.envelope_line_id:
            touched |= self._consume_envelope(inv_amls)
        return self._open_orders(touched)

    def _open_orders(self, orders):
        if len(orders) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "res_id": orders.id,
                "view_mode": "form",
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.ids)],
        }

    # -- consommation de l'enveloppe « frais divers » ---------------------------------
    def _consume_envelope(self, inv_amls):
        """Retire de la ligne d'enveloppe le montant rapproché (au plus son reste) et transfère la revente
        correspondante, au prorata, aux lignes de BC qui portent maintenant la facture."""
        self.ensure_one()
        line = self.envelope_line_id
        order = line.order_id
        deducted, overrun, total = self._envelope_amounts()
        rounding = self.move_id.currency_id.rounding or 0.01
        if float_is_zero(deducted, precision_rounding=rounding) or not total:
            return self.env["purchase.order"]
        resell_net = sum(order.order_line.mapped("reselling_subtotal"))
        transfer = resell_net * deducted / total
        # trace visible dans le BC : une ligne négative du montant de la facture consommée (et de la revente
        # transférée) ; son nom n'est qu'un libellé, le retour arrière passe par consumed_by_move_id. En cas de
        # dépassement, une ligne positive du même montant le compense pour que le total du BC soit exactement 0.
        base_vals = {
            "order_id": order.id,
            "product_id": line.product_id.id,
            "product_qty": 1.0,
            "product_uom": line.product_uom.id,
            "taxes_id": [Command.set(line.taxes_id.ids)],
            "analytic_distribution": line.analytic_distribution,
            "previsional_invoice_date": line.previsional_invoice_date,
            "consumed_by_move_id": self.move_id.id,  # identifie les lignes de trace et leur facture
        }
        reference = self.move_id.display_name  # libellé d'affichage ; l'identification passe par consumed_by_move_id
        self.env["purchase.order.line"].create(
            {
                **base_vals,
                "name": "Consommé par %s" % reference,
                "price_unit": -(deducted + overrun),
                "reselling_price_unit": -transfer,
                "reselling_subtotal": -transfer,
            }
        )
        if overrun:
            self.env["purchase.order.line"].create(
                {
                    **base_vals,
                    "name": "Dépassement de l'enveloppe — %s" % reference,
                    "price_unit": overrun,
                    "reselling_price_unit": 0.0,
                    "reselling_subtotal": 0.0,
                }
            )
        # revente et date prévisionnelle suivent les lignes du vrai BC
        invoiced = sum(inv_amls.mapped("price_subtotal")) or 1.0
        for aml in inv_amls:
            weight = aml.price_subtotal / invoiced
            tgt = aml.purchase_line_id
            vals = {}
            if tgt.product_qty:
                vals["reselling_price_unit"] = tgt.reselling_price_unit + transfer * weight / tgt.product_qty
            if line.previsional_invoice_date and not tgt.previsional_invoice_date:
                vals["previsional_invoice_date"] = line.previsional_invoice_date
            if vals:
                tgt.write(vals)
        targets = inv_amls.mapped("purchase_line_id")
        note = self.env._(
            "Enveloppe « frais divers » consommée par la facture %(move)s : %(amount)s retiré.",
            move=self.move_id.display_name,
            amount=self.move_id.currency_id.format(deducted),
        )
        if overrun:
            note += " " + self.env._(
                "Dépassement de %(amount)s : l'enveloppe est ramenée à 0.",
                amount=self.move_id.currency_id.format(overrun),
            )
        order.message_post(body=note)
        targets.mapped("order_id").message_post(body=note)
        if float_is_zero(order.amount_untaxed, precision_rounding=rounding):
            order.button_cancel()  # annulé et non supprimé : l'historique est conservé, les totaux du projet l'ignorent
        return order

    # -- cas 1 : création du BC ------------------------------------------------
    def _do_create_order(self, amls):
        move = self.move_id
        project = self.project_ids
        amls = amls.filtered("product_id")
        if not amls:
            raise UserError("Aucune ligne de facture avec un produit : impossible de créer le BC.")
        # project_accounting exige que le fournisseur soit déclaré sur le projet (onglet Achats) :
        # on crée le lien projet / fournisseur s'il n'existe pas encore, avec le type choisi dans le wizard.
        link = self.env["project.outsourcing.link"]
        if not link.search_count([("project_id", "=", project.id), ("partner_id", "=", move.partner_id.id)]):
            link.create(
                {"project_id": project.id, "partner_id": move.partner_id.id, "link_type": self.link_type or "other"}
            )
        vals_list = amls._prepare_line_values_for_purchase()
        for vals in vals_list:
            if not vals.get("analytic_distribution") and project.account_id:
                vals["analytic_distribution"] = {str(project.account_id.id): 100}
        order = self.env["purchase.order"].create(
            {
                "partner_id": move.partner_id.id,
                "order_line": [Command.create(v) for v in vals_list],
            }
        )
        order.button_confirm()
        for aml, pol in zip(amls, order.order_line):
            aml.purchase_line_id = pol.id
        return order

    # -- rattachement seul (lignes inter-société) -------------------------------
    def _do_attach_only(self, amls, wpols):
        pols = wpols.mapped("purchase_line_id")
        if len(pols) == 1:
            amls.write({"purchase_line_id": pols.id})
        else:
            for aml, pol in zip(amls, pols):
                aml.purchase_line_id = pol.id
        return pols.mapped("order_id")

    # -- mode consommation ------------------------------------------------------
    def _do_consumption(self, amls, wpols):
        pairs = [(wpols, amls)] if len(wpols) == 1 else [(w, a) for w, a in zip(wpols, amls)]
        touched = self.env["purchase.order"]
        for w, aml_group in pairs:
            pol = w.purchase_line_id
            consumed, qty_open = w.qty_consumed, w.qty_open
            if float_compare(consumed, qty_open, precision_digits=4) == 0 and not pol.qty_invoiced:
                target = pol  # dernière tranche : pas de scission, pas de ligne fantôme à zéro
            else:
                price_unit = pol.price_unit
                resell = pol.reselling_price_unit
                target = pol.copy(
                    {
                        "product_qty": consumed,
                        "price_unit": price_unit,
                        "reselling_price_unit": resell,
                        "reselling_subtotal": resell * consumed,
                    }
                )
                pol.write({"product_qty": pol.product_qty - consumed, "price_unit": price_unit})
            target.qty_invoiced_override = True
            aml_group.write({"purchase_line_id": target.id})
            touched |= pol.order_id
        return touched

    # -- mode remplacement ------------------------------------------------------
    def _do_replacement(self, amls, wpols):
        rounding = self.move_id.currency_id.rounding or 0.01
        pool = amls
        touched = self.env["purchase.order"]
        for order in wpols.mapped("order_id"):
            group = wpols.filtered(lambda w, o=order: w.order_id == o)
            target = sum(group.mapped("amount_open"))
            mine = self._take_subset(pool, target, rounding)
            pool -= mine
            self._replace_in_order(order, group, mine, rounding)
            touched |= order
        if pool:
            raise UserError("Des lignes de facture cochées n'ont pu être affectées à aucune ligne de BC.")
        return touched

    @api.model
    def _take_subset(self, amls, target, rounding):
        items = [(aml.id, aml.price_subtotal) for aml in amls]
        found = self._find_subsets(items, target, rounding, limit=1)
        if not found:
            raise UserError(
                "Impossible d'affecter les lignes de facture cochées à ce BC : aucune combinaison de lignes "
                "de facture ne totalise %.2f." % target
            )
        return amls.filtered(lambda a: a.id in found[0])

    def _replace_in_order(self, order, group, amls, rounding):
        pool = amls
        # 1) lignes partiellement facturées : jamais supprimées, scindées (part ouverte -> nouvelle ligne)
        for w in group.filtered(lambda x: x.state == "partial"):
            sub = self._take_subset(pool, w.amount_open, rounding)
            pool -= sub
            new_pol = self._split_by_amount(w.purchase_line_id, w.amount_open)
            sub.write({"purchase_line_id": new_pol.id})
        # 2) lignes ouvertes : remplacées par des lignes recopiées depuis la facture
        normal = group.filtered(lambda x: x.state != "partial").mapped("purchase_line_id")
        if not normal:
            if pool:
                raise UserError("Des lignes de facture cochées n'ont pu être affectées à aucune ligne de BC.")
            return
        total_resell = sum(normal.mapped("reselling_subtotal"))
        total_new = sum(pool.mapped("price_subtotal"))
        for aml in pool:
            tmpl = self._pick_template(normal, aml)
            vals = aml._prepare_line_values_for_purchase()[0] if aml.product_id else {
                "product_id": tmpl.product_id.id,
                "product_qty": aml.quantity,
                "product_uom": aml.product_uom_id.id or tmpl.product_uom.id,
                "price_unit": aml.price_unit,
                "discount": aml.discount,
            }
            share = aml.price_subtotal / total_new if total_new else 0.0
            vals.update(
                {
                    "order_id": order.id,
                    "name": aml.name or tmpl.name,
                    "analytic_distribution": tmpl.analytic_distribution,
                    "previsional_invoice_date": tmpl.previsional_invoice_date,
                    "date_planned": tmpl.date_planned,
                    "sequence": tmpl.sequence,
                    "taxes_id": [Command.set(tmpl.taxes_id.ids)],
                    # reselling_price_unit seul est remis à 0 par l'inverse de reselling_subtotal à la création
                    "reselling_subtotal": total_resell * share,
                    "reselling_price_unit": (total_resell * share / aml.quantity) if aml.quantity else 0.0,
                }
            )
            new_pol = self.env["purchase.order.line"].create(vals)
            aml.purchase_line_id = new_pol.id
        normal.with_context(bill_po_reconcile_replace=True).unlink()

    @api.model
    def _pick_template(self, pols, aml):
        accounts = _analytic_accounts(aml.analytic_distribution)
        for pol in pols:
            if accounts & _analytic_accounts(pol.analytic_distribution):
                return pol
        return pols[:1]

    @api.model
    def _split_by_amount(self, pol, amount_open):
        """Ligne partiellement facturée : la part facturée reste sur la ligne d'origine (même id, même quantité,
        montant ramené à ce qui est facturé), la part ouverte part sur une ligne nouvelle."""
        subtotal = pol.price_subtotal
        if not subtotal:
            raise UserError("Ligne de BC à montant nul : scission impossible.")
        ratio_open = amount_open / subtotal
        ratio_invoiced = 1.0 - ratio_open
        price_unit, resell = pol.price_unit, pol.reselling_price_unit
        new_pol = pol.copy(
            {
                "price_unit": price_unit * ratio_open,
                "reselling_price_unit": resell * ratio_open,
                "reselling_subtotal": resell * ratio_open * pol.product_qty,
                "qty_invoiced_override": True,
            }
        )
        pol.write({"price_unit": price_unit * ratio_invoiced, "reselling_price_unit": resell * ratio_invoiced})
        return new_pol


class BillPoReconcileSuggestion(models.TransientModel):
    _name = "bill.po.reconcile.suggestion"
    _description = "Suggestion de projet / BC pour une facture sans projet"
    _order = "sequence, id"

    wizard_id = fields.Many2one("bill.po.reconcile.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    sequence = fields.Integer()
    project_id = fields.Many2one("project.project", string="Projet", readonly=True)
    order_id = fields.Many2one("purchase.order", string="BC", readonly=True)
    amount_open = fields.Monetary("Reste à facturer", readonly=True, currency_field="currency_id")
    reasons = fields.Char("Pourquoi", readonly=True)
    score = fields.Float(readonly=True)
    selected = fields.Boolean("Cocher")


class BillPoReconcileInvoiceLine(models.TransientModel):
    _name = "bill.po.reconcile.invoice.line"
    _description = "Ligne de facture du rapprochement"

    wizard_id = fields.Many2one("bill.po.reconcile.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    move_line_id = fields.Many2one("account.move.line", readonly=True)
    name = fields.Char(readonly=True)
    quantity = fields.Float(readonly=True)
    price_unit = fields.Float(readonly=True)
    price_subtotal = fields.Monetary(readonly=True, currency_field="currency_id")
    linked = fields.Boolean("Déjà rapprochée", readonly=True)
    selected = fields.Boolean("Cocher")


class BillPoReconcilePoLine(models.TransientModel):
    _name = "bill.po.reconcile.po.line"
    _description = "Ligne de BC du rapprochement"

    wizard_id = fields.Many2one("bill.po.reconcile.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    purchase_line_id = fields.Many2one("purchase.order.line", readonly=True)
    order_id = fields.Many2one("purchase.order", readonly=True)
    name = fields.Char(readonly=True)
    product_qty = fields.Float(readonly=True)
    price_unit = fields.Float(readonly=True)
    price_subtotal = fields.Monetary(readonly=True, currency_field="currency_id")
    state = fields.Selection(BILLING_STATES, readonly=True)
    amount_invoiced = fields.Monetary(readonly=True, currency_field="currency_id")
    amount_open = fields.Monetary("Reste à facturer", readonly=True, currency_field="currency_id")
    qty_open = fields.Float("Qté restante", readonly=True)
    qty_consumed = fields.Float("Qté consommée")
    is_mirror = fields.Boolean("Inter-société", readonly=True)
    analytic_ok = fields.Boolean(default=True, readonly=True)
    selectable = fields.Boolean(readonly=True)
    selected = fields.Boolean("Cocher")
