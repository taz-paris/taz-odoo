from odoo import Command, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    # Document-level EN16931 references with no dedicated field in
    # account_invoice_en16931/l10n_fr_account_invoice_en16931: each BT below
    # is 0..1 per invoice, so a plain field is enough (no need for a
    # generic N-to-1 reference model).
    l10n_fr_bt12_contract_reference = fields.Char(string="Référence du contrat (BT-12)")
    l10n_fr_bt15_receiving_advice_reference = fields.Char(
        string="Référence d'avis de réception (BT-15)"
    )
    l10n_fr_bt16_despatch_advice_reference = fields.Char(
        string="Référence d'avis d'expédition (BT-16)"
    )
    l10n_fr_bt17_tender_reference = fields.Char(
        string="Référence de l'appel d'offres ou du lot (BT-17)"
    )
    l10n_fr_bt18_invoiced_object_reference = fields.Char(
        string="Identifiant d'objet facturé (BT-18)"
    )
    l10n_fr_bt18_invoiced_object_scheme = fields.Char(
        string="Schéma de l'identifiant d'objet facturé (BT-18-1)"
    )
    l10n_fr_bt19_buyer_accounting_reference = fields.Char(
        string="Référence comptable de l'acheteur (BT-19)"
    )

    def _prepare_en16931_dict(self, speedy, pdf_invoice_bin=False):
        vals = super()._prepare_en16931_dict(speedy, pdf_invoice_bin=pdf_invoice_bin)
        project_numbers = [n for n in self.rel_project_ids.mapped("number") if n]
        if project_numbers:
            vals["BT-11"] = "/".join(project_numbers)
            project_names = [n for n in self.rel_project_ids.mapped("name") if n]
            if project_names:
                vals["BT-11-0"] = "/".join(project_names)
        if self.l10n_fr_bt12_contract_reference:
            vals["BT-12"] = self.l10n_fr_bt12_contract_reference
        if self.l10n_fr_bt15_receiving_advice_reference:
            vals["BT-15"] = self.l10n_fr_bt15_receiving_advice_reference
        if self.l10n_fr_bt16_despatch_advice_reference:
            vals["BT-16"] = self.l10n_fr_bt16_despatch_advice_reference
        if self.l10n_fr_bt17_tender_reference:
            # BT-17 is 0..n in the EXTENDED profile but capped to a single
            # element at en16931/CIUS-FR level; the library still expects a
            # list.
            vals["BT-17"] = [self.l10n_fr_bt17_tender_reference]
        if self.l10n_fr_bt18_invoiced_object_reference:
            # BT-18 is keyed by its scheme identifier (BT-18-1).
            scheme = self.l10n_fr_bt18_invoiced_object_scheme or ""
            vals["BT-18"] = {scheme: self.l10n_fr_bt18_invoiced_object_reference}
        if self.l10n_fr_bt19_buyer_accounting_reference:
            vals["BT-19"] = self.l10n_fr_bt19_buyer_accounting_reference
        return vals

    def action_open_bill_po_reconcile(self):
        """Ouvre le rapprochement facture fournisseur / bon de commande (remplace « Purchase Matching »)."""
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund"):
            raise UserError(self.env._("Le rapprochement ne s'applique qu'aux factures et avoirs fournisseur."))
        if not self.partner_id:
            raise UserError(self.env._("Renseignez d'abord le fournisseur de la facture."))
        wizard = self.env["bill.po.reconcile.wizard"].create(
            {"move_id": self.id, "project_ids": [Command.set(self.rel_project_ids.ids)]}
        )
        if self.rel_project_ids:
            wizard._onchange_project_ids()
        else:
            wizard._build_suggestions()  # projet inconnu : suggestions de projet / BC du fournisseur
        return wizard._reopen()

    def _envelope_consumption_lines(self):
        """Lignes « Consommé par… » (négatives) et « Dépassement… » (positives) portées par le BC du fournisseur
        « frais divers », identifiées par `consumed_by_move_id` : trace visible de la consommation et point d'entrée
        du retour arrière."""
        self.ensure_one()
        return self.env["purchase.order.line"].search([("consumed_by_move_id", "=", self.id)])

    def _restore_envelope_consumptions(self, fraction=1.0):
        """Remet à l'enveloppe `fraction` (0..1) de ce que cette facture lui retire encore, et reprend aux lignes
        du vrai BC la revente correspondante. Les lignes « Consommé par… » (négatives) et « Dépassement… »
        (positives) sont réduites dans la même proportion ; à 100 % elles sont supprimées."""
        for move in self:
            rounding = move.currency_id.rounding or 0.01
            lines = move._envelope_consumption_lines()
            for order in lines.order_id:
                olines = lines.filtered(lambda l, o=order: l.order_id == o)
                consumed = -sum(olines.mapped("price_subtotal"))  # montant réellement retiré de l'enveloppe
                resell = -sum(olines.mapped("reselling_subtotal"))
                if float_is_zero(consumed, precision_rounding=rounding):
                    continue
                if order.state == "cancel":
                    order.button_draft()
                    order.button_confirm()
                # revente reprise aux lignes du vrai BC, au prorata des montants de facture qu'elles portent
                amls = move.invoice_line_ids.filtered("purchase_line_id")
                invoiced = sum(amls.mapped("price_subtotal")) or 1.0
                for aml in amls:
                    target = aml.purchase_line_id
                    if target.product_qty:
                        share = resell * fraction * aml.price_subtotal / invoiced
                        target.write({"reselling_price_unit": target.reselling_price_unit - share / target.product_qty})
                if float_compare(fraction, 1.0, precision_rounding=0.0001) >= 0:
                    olines.with_context(bill_po_reconcile_replace=True).unlink()
                else:
                    for cline in olines:
                        keep = 1.0 - fraction
                        cline.write(
                            {
                                "price_unit": cline.price_unit * keep,
                                "reselling_price_unit": cline.reselling_price_unit * keep,
                                "reselling_subtotal": cline.reselling_subtotal * keep,
                            }
                        )
                order.message_post(
                    body=self.env._(
                        "%(amount)s remis à l'enveloppe suite à l'annulation ou à l'avoir de la facture %(move)s.",
                        amount=move.currency_id.format(consumed * fraction),
                        move=move.display_name,
                    )
                )

    def button_cancel(self):
        res = super().button_cancel()
        self._restore_envelope_consumptions(1.0)
        return res

    def unlink(self):
        self._restore_envelope_consumptions(1.0)
        return super().unlink()

    def action_post(self):
        res = super().action_post()
        for refund in self.filtered(lambda m: m.move_type == "in_refund" and m.reversed_entry_id):
            origin = refund.reversed_entry_id
            previous = sum(
                origin.reversal_move_ids.filtered(lambda m: m.state == "posted" and m != refund).mapped("amount_untaxed")
            )
            remaining = origin.amount_untaxed - previous
            fraction = min(refund.amount_untaxed / remaining, 1.0) if remaining > 0 else 1.0
            origin._restore_envelope_consumptions(fraction)
        return res
