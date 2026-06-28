from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .project_outsourcing_link import OUTSOURCING_LINK_TYPES

import datetime

import logging
from odoo import _
_logger = logging.getLogger(__name__)

class ProjectProgress(models.Model):
    _name = 'project.progress'
    _description = 'Avancement Projet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rel_closing_date desc, type desc, id asc'

    _sql_constraints = [
        ('unique_closing_link', 'UNIQUE NULLS NOT DISTINCT (accounting_closing_id, outsourcing_link_id)', 
         'Il ne peut y avoir qu\'un seul avancement par couple clôture / lien de sous-traitance.')
    ]

    # --- Champs relationnels ---
    accounting_closing_id = fields.Many2one('project.accounting_closing', string="Clôture comptable", required=True, ondelete='restrict')
    rel_closing_date = fields.Date(related='accounting_closing_id.closing_date', string="Date de clôture", store=True)
    outsourcing_link_id = fields.Many2one('project.outsourcing.link', string="Lien projet / fournisseur", store=True)
    rel_project_id = fields.Many2one('project.project', related='accounting_closing_id.project_id', string="Projet", store=True)
    rel_project_user_id = fields.Many2one(related='rel_project_id.user_id', string="Directeur de mission", store=True)
    rel_project_manager_user_id = fields.Many2one(related='rel_project_id.project_manager.user_id', string="Partner ou manager en appui", store=True)
    rel_original_stage_id = fields.Many2one(related='accounting_closing_id.original_stage_id', string="Statut début clôture", store=True)
    rel_outsourcing_partner_id = fields.Many2one(related='outsourcing_link_id.partner_id', string="Fournisseur", store=True)
    rel_is_alliance_partner = fields.Boolean(related='rel_outsourcing_partner_id.is_alliance_partner', store=True)
    
    company_id = fields.Many2one('res.company', string='Société', required=True, related="accounting_closing_id.company_id")
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Devise", readonly=True)

    auto_compute_provisions = fields.Boolean('Calcul FNP/CCA auto', default=True, readonly=True, help="Si coché, les CCA et FNP de cet avancement sont calculés automatiquement.")

    # --- Classification ---
    type = fields.Selection([('internal_production', 'Production interne')] + OUTSOURCING_LINK_TYPES, 
                            string="Type", compute='_compute_type', store=True)

    # --- Navigation ---
    previous_progress_id = fields.Many2one('project.progress', string="Avancement précédent", 
                                          compute='_compute_previous_progress_id', store=True)
    next_progress = fields.Many2one('project.progress', string="Avancement suivant", compute='_compute_next_progress')

    # --- Related précédent ---
    rel_previous_progress_cost_amount = fields.Monetary(related='previous_progress_id.progress_cost_amount', string="Coût de revient cumulé précédent")
    rel_previous_progress_revenue_rate = fields.Float(related='previous_progress_id.progress_revenue_rate', aggregator=False, string="CA cumulé en % précédent")
    rel_previous_progress_revenue_amount = fields.Monetary(related='previous_progress_id.progress_revenue_amount', string="CA cumulé en € précédent")

    # --- Projections à terminaison ---
    target_project_cost = fields.Monetary(string="Coût de revient total projeté", compute='_compute_target_project_cost', inverse='_inverse_target_project_cost', store=True, readonly=False)
    target_project_revenue = fields.Monetary(string="CA total projeté", compute='_compute_target_project_revenue', store=True)
    target_project_margin = fields.Monetary(string="Marge projetée en €", compute='_compute_target_project_margin', store=True)
    target_project_margin_rate = fields.Float(string="Marge projetée en %", aggregator=None, compute='_compute_target_project_margin_rate', store=True, digits=(16, 10))

    # --- Quantités S/T ---
    target_project_outsourcing_product_qty = fields.Float(string="Nb unités commandées", compute='_compute_target_project_outsourcing_product_qty', store=True, digits=(16, 10))
    outsourcing_product_qty = fields.Float(string="Nb unités produites", compute='_compute_outsourcing_product_qty', inverse='_inverse_outsourcing_product_qty', store=True, readonly=False, digits=(16, 10))
    outsourcing_product_qty_period = fields.Float(string="Nb unités produites période", compute='_compute_qty_period', inverse='_inverse_qty_period', store=True, readonly=False, digits=(16, 10))

    # --- Avancement cumulé ---
    progress_cost_amount = fields.Monetary(string="Coût de revient", compute='_compute_progress_cost_amount', store=True)
    progress_revenue_rate = fields.Float(string="CA cumulé en %", aggregator=False, compute='_compute_progress_revenue_rate', inverse='_inverse_progress_revenue_rate', store=True, readonly=False, digits=(16, 10))
    progress_revenue_amount = fields.Monetary(string="CA cumulé en €", 
                                             compute='_compute_progress_revenue_amount', inverse='_inverse_revenue', store=True, readonly=False)
    progress_revenue_margin = fields.Monetary(string="Marge en €", 
                                             compute='_compute_progress_revenue_margin', store=True)
    progress_revenue_margin_rate = fields.Float(string="Marge en %", aggregator=False,
                                             compute='_compute_progress_revenue_margin_rate', store=True, digits=(16, 10))
    # --- Avancement période ---
    progress_cost_amount_period = fields.Monetary(string="Coût de revient période", 
                                                 compute='_compute_progress_cost_amount_period', store=True)
    progress_revenue_rate_period = fields.Float(string="CA période en % du prix de vente", aggregator=False, compute='_compute_progress_revenue_rate_period', inverse='_inverse_progress_revenue_rate_period', store=True, readonly=False, digits=(16, 10))
    progress_revenue_amount_period = fields.Monetary(string="CA période en €", 
                                                    compute='_compute_progress_revenue_amount_period', store=True)
    progress_revenue_margin_period = fields.Monetary(string="Marge période en €", 
                                                    compute='_compute_progress_revenue_margin_period', store=True)
    progress_revenue_margin_rate_period = fields.Float(string="Marge période en %", aggregator=False,
                                                    compute='_compute_progress_revenue_margin_rate_period', store=True, digits=(16, 10))

    # --- Provisions ---
    purchase_period_amount = fields.Monetary('Achats HT sur la periode', compute='_compute_purchase_period_amount', store=True)

    cca_previous_balance = fields.Monetary('Précédent solde CCA', compute='_compute_cca_previous_balance', aggregator='sum', store=True)
    cca_period_amount = fields.Monetary('CCA(+)', compute='_compute_cca_period_amount', store=True)
    cca_balance = fields.Monetary('Solde CCA', compute='_compute_provisions_balances', store=True, aggregator='sum')

    fnp_previous_balance = fields.Monetary('Précédent solde FNP', compute='_compute_fnp_previous_balance', aggregator='sum', store=True)
    fnp_period_amount = fields.Monetary('FNP(-)', compute='_compute_fnp_period_amount', store=True)
    fnp_balance = fields.Monetary('Solde FNP', compute='_compute_provisions_balances', store=True, aggregator='sum')

    # --- Autres calculs ---
    future_staffing_days = fields.Float(string="Jours restant à produire", help="Somme des jours staffés dans Napta (tous grades confondus) pour les périodes de staffing qui commencent après la date de clôture. Valeur telle que disponible dans TazForce à date du dernier rafraichissement forcé.", compute='_compute_future_staffing_days', store=True)
    price_unit = fields.Monetary(string="TJM sous-traitance", compute='_compute_price_unit', store=True)
    reselling_price_unit = fields.Monetary(string="TJM revente sous-traitant", compute='_compute_reselling_price_unit', store=True)

    is_validated = fields.Boolean(string="Validé", tracking=True)
    comment = fields.Html("Commentaire")
    rel_previous_progress_comment = fields.Html("Commentaire période précédente", related='previous_progress_id.comment')

    # ===================================================================
    # DISPLAY NAME
    # ===================================================================
    @api.depends('rel_project_id.name', 'rel_closing_date', 'type', 'outsourcing_link_id.display_name')
    def _compute_display_name(self):
        for rec in self:
            date_str = rec.rel_closing_date.strftime('%m/%Y') if rec.rel_closing_date else _('N/A')
            project_label = rec.rel_project_id.name or _('N/A')
            if rec.type == 'internal_production':
                origin = _("Prod. Interne")
            elif rec.outsourcing_link_id:
                origin = rec.outsourcing_link_id.display_name
            else:
                origin = " "
            rec.display_name = f"{project_label} ({date_str}) - {origin}"

    # ===================================================================
    # WRITE / UNLINK
    # ===================================================================
    def write(self, vals):
        for rec in self:
            rec._check_can_write(vals)
        res = super().write(vals)
        return res

    def _check_can_write(self, vals=None):
        # On est obligé d'appeler cette fonction dans chaque fonction @depends car elles bypass write()
        #       Avant on ne contrôlait que dans write() et certaines valeur on été réécrites alors quel l'objet était déjà validé
        self.ensure_one()
        if hasattr(models, 'NewId') and isinstance(self.id, models.NewId):
            return
        if self.accounting_closing_id.is_validated:
            import traceback
            _logger.info("".join(traceback.format_stack()))
            _logger.info(vals)
            raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est lié à une clôture validée. project_progress_id=%s" % self.id))
        if self.next_progress:
            raise ValidationError(_("Il n'est pas possible de modifier cet avancement car un avancement postérieur existe. project_progress_id=%s" % self.id))
        if self.is_validated:
            #import traceback
            #_logger.info("".join(traceback.format_stack()))
            #_logger.info(vals)
            if vals is None:
                raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est validé. project_progress_id=%s" % self.id))
            else:
                for val_key in vals.keys():
                    if val_key not in ['is_validated', 'message_follower_ids', 'message_ids', 'activity_ids', 'message_attachment_ids', 'message_main_attachment_id']:
                        raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est validé.\n\nTentative de modification de l'attribut : %s") % val_key)

    def unlink(self):
        for rec in self:
            if rec.next_progress:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car un avancement postérieur existe."))
            if rec.is_validated:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car il est validé."))
        return super().unlink()

    # ===================================================================
    # COMPUTE / INVERSE — un couple par champ calculé
    # ===================================================================

    # --- type ---
    @api.depends('outsourcing_link_id', 'outsourcing_link_id.link_type')
    def _compute_type(self):
        for rec in self:
            rec._check_can_write()
            rec.type = rec.outsourcing_link_id.link_type if rec.outsourcing_link_id else 'internal_production'

    # --- previous_progress_id ---
    @api.depends('accounting_closing_id', 'accounting_closing_id.previous_closing', 'outsourcing_link_id')
    def _compute_previous_progress_id(self):
        for rec in self:
            rec._check_can_write()
            previous_closing = rec.accounting_closing_id.previous_closing
            if previous_closing:
                rec.previous_progress_id = self.env['project.progress'].search([
                    ('accounting_closing_id', '=', previous_closing.id),
                    ('outsourcing_link_id', '=', rec.outsourcing_link_id.id)
                ], limit=1)
            else:
                rec.previous_progress_id = False

    # --- next_progress (non stocké, recalculé à chaque accès) ---
    def _compute_next_progress(self):
        for rec in self:
            real_id = rec._origin.id if hasattr(rec, '_origin') and rec._origin else rec.id
            if real_id and not isinstance(real_id, models.NewId):
                rec.next_progress = self.env['project.progress'].search([('previous_progress_id', '=', real_id)], limit=1)
            else:
                rec.next_progress = False

    # --- target_project_cost ---
    # Dépend uniquement de type et outsourcing_link_id (positionnés à la création).
    # Pas de dépendance sur rel_project_id.company_part_* pour éviter l'écrasement
    # des valeurs lorsque les données du projet changent a posteriori.
    @api.depends('type', 'outsourcing_link_id')
    def _compute_target_project_cost(self):
        for rec in self:
            rec._check_can_write()
            if rec.type == 'internal_production':
                rec.target_project_cost = (rec.rel_project_id.company_part_cost_current or 0.0) + (rec.rel_project_id.company_part_cost_futur or 0.0)
            elif rec.outsourcing_link_id:
                rec.target_project_cost = rec.outsourcing_link_id.order_company_payment_amount or 0.0
            else:
                rec.target_project_cost = 0.0

    def _inverse_target_project_cost(self):
        pass  # Accepte la valeur saisie manuellement

    # --- target_project_revenue ---
    # Dépend uniquement de type et outsourcing_link_id (positionnés à la création).
    # Pas de dépendance sur rel_project_id.company_part_* pour éviter l'écrasement
    # des valeurs lorsque les données du projet changent a posteriori.
    @api.depends('type', 'outsourcing_link_id')
    def _compute_target_project_revenue(self):
        for rec in self:
            rec._check_can_write()
            if rec.type == 'internal_production':
                rec.target_project_revenue = rec.rel_project_id.company_part_amount_current or 0.0
            elif rec.outsourcing_link_id:
                if rec.outsourcing_link_id.order_sum_purchase_order_lines:
                    indirect_payment_ratio = rec.outsourcing_link_id.order_company_payment_amount / rec.outsourcing_link_id.order_sum_purchase_order_lines
                else:
                    indirect_payment_ratio = 1.0
                rec.target_project_revenue = (rec.outsourcing_link_id.outsource_part_amount_current or 0.0) * indirect_payment_ratio
            else:
                rec.target_project_revenue = 0.0


    # --- target_project_margin ---
    @api.depends('target_project_revenue', 'target_project_cost')
    def _compute_target_project_margin(self):
        for rec in self:
            rec._check_can_write()
            rec.target_project_margin = (rec.target_project_revenue or 0.0) - (rec.target_project_cost or 0.0)

    # --- target_project_margin_rate ---
    @api.depends('target_project_margin', 'target_project_revenue')
    def _compute_target_project_margin_rate(self):
        for rec in self:
            rec._check_can_write()
            if rec.target_project_revenue:
                rec.target_project_margin_rate = (rec.target_project_margin or 0.0) / rec.target_project_revenue
            else:
                rec.target_project_margin_rate = 0.0

    # --- target_project_outsourcing_product_qty ---
    # Cette fonction est executée une seule fois à la création.
    # Pas de dépendance sur outsourcing_link_id.order_sum_purchase_order_product_qty pour éviter l'écrasement
    # des valeurs lorsque les données du BCF changent a posteriori.
    # En revanche il est indispensable de dépendre de outsourcing_link_id sinon la valeur n'est pas initialisée
    @api.depends('type', 'outsourcing_link_id')
    def _compute_target_project_outsourcing_product_qty(self):
        for rec in self:
            rec._check_can_write()
            rec.target_project_outsourcing_product_qty = rec.outsourcing_link_id.order_sum_purchase_order_product_qty if rec.outsourcing_link_id else 0.0

    # --- Quantités S/T ---
    @api.depends('progress_revenue_rate', 'target_project_outsourcing_product_qty')
    def _compute_outsourcing_product_qty(self):
        for rec in self:
            rec._check_can_write()
            rec.outsourcing_product_qty = (rec.progress_revenue_rate or 0.0) * (rec.target_project_outsourcing_product_qty or 0.0)

    def _inverse_outsourcing_product_qty(self):
        for rec in self:
            rec._check_can_write()
            target_qty = rec.target_project_outsourcing_product_qty or 0.0
            rec.progress_revenue_rate = (rec.outsourcing_product_qty / target_qty) if target_qty else 0.0

    # --- outsourcing_product_qty_period ---
    @api.depends('progress_revenue_rate_period', 'target_project_outsourcing_product_qty')
    def _compute_qty_period(self):
        for rec in self:
            rec._check_can_write()
            rec.outsourcing_product_qty_period = (rec.progress_revenue_rate_period or 0.0) * (rec.target_project_outsourcing_product_qty or 0.0)

    def _inverse_qty_period(self):
        for rec in self:
            rec._check_can_write()
            # 1. On déduit le taux d'avancement de la période par rapport au budget cible actuel (en Jours/Unités)
            target_qty = rec.target_project_outsourcing_product_qty or 0.0
            rate_period = (rec.outsourcing_product_qty_period / target_qty) if target_qty else 0.0
            
            # 2. On traduit ce taux en Euros produits sur la période
            period_amount = (rec.target_project_revenue or 0.0) * rate_period
            
            # 3. On ajoute ce montant au cumul précédent
            rec.progress_revenue_amount = (rec.rel_previous_progress_revenue_amount or 0.0) + period_amount
            # La cascade Odoo prendra le relais pour mettre à jour progress_revenue_rate et outsourcing_product_qty

    # --- progress_cost_amount ---
    @api.depends('type', 'rel_project_id', 'rel_closing_date',
                 'target_project_cost', 'progress_revenue_rate', 'outsourcing_product_qty', 'target_project_outsourcing_product_qty')
    def _compute_progress_cost_amount(self):
        for rec in self:
            rec._check_can_write()
            if rec.type == 'internal_production':
                rec.progress_cost_amount = -rec.rel_project_id.get_production_cost(
                    [('date', '<=', rec.rel_closing_date), ('category', '=', 'project_employee_validated')],
                    force_recompute_amount=False)[0]
            elif rec.outsourcing_link_id:
                if rec.type == 'other':
                    if rec.rel_closing_date >= datetime.date(2026, 1, 1): 
                        # Les données saisies manuellement sur les avancements d'initialisation de décembre 2026 ne doivent pas bouger
                        purchase_period_subtotal, purchase_period_total, purchase_period_paid, purchase_period_line_ids = rec.rel_project_id.compute_account_move_total_all_partners([('partner_id', '=', rec.outsourcing_link_id.partner_id.id), ('date', '<=', rec.rel_closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['in_refund', 'in_invoice'])])
                        rec.progress_cost_amount = -1 * purchase_period_subtotal
                else :
                    rec.progress_cost_amount = (rec.target_project_cost or 0.0) * (rec.progress_revenue_rate or 0.0)
            else:
                rec.progress_cost_amount = 0.0

    # --- progress_revenue_rate ---
    @api.depends('type', 'progress_cost_amount', 'target_project_cost')
    def _compute_progress_revenue_rate(self):
        for rec in self:
            rec._check_can_write()
            if rec.type in ['internal_production', 'other']:
                rec.progress_revenue_rate = (rec.progress_cost_amount / rec.target_project_cost) if rec.target_project_cost else 0.0

    def _inverse_progress_revenue_rate(self):
        pass # Le taux est stocké, les autres champs en dépendent.

    # --- progress_revenue_amount ---
    @api.depends('target_project_revenue', 'progress_revenue_rate')
    def _compute_progress_revenue_amount(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_revenue_amount = (rec.target_project_revenue or 0.0) * (rec.progress_revenue_rate or 0.0)

    def _inverse_revenue(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_revenue_rate = (rec.progress_revenue_amount / rec.target_project_revenue) if rec.target_project_revenue else 0.0

    # --- progress_revenue_margin ---
    @api.depends('progress_revenue_amount', 'progress_cost_amount')
    def _compute_progress_revenue_margin(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_revenue_margin = (rec.progress_revenue_amount or 0.0) - (rec.progress_cost_amount or 0.0)    
    
    # --- progress_revenue_margin_rate ---
    @api.depends('progress_revenue_margin', 'progress_revenue_amount')
    def _compute_progress_revenue_margin_rate(self):
        for rec in self:
            rec._check_can_write()
            if rec.progress_revenue_amount:
                rec.progress_revenue_margin_rate = (rec.progress_revenue_margin or 0.0) / rec.progress_revenue_amount
            else:
                rec.progress_revenue_margin_rate = 0.0
    
    # --- progress_revenue_rate_period ---
    @api.depends('progress_revenue_amount_period', 'target_project_revenue')
    def _compute_progress_revenue_rate_period(self):
        for rec in self:
            rec._check_can_write()
            if rec.target_project_revenue:
                rec.progress_revenue_rate_period = (rec.progress_revenue_amount_period or 0.0) / rec.target_project_revenue
            else:
                rec.progress_revenue_rate_period = 0.0

    def _inverse_progress_revenue_rate_period(self):
        for rec in self:
            rec._check_can_write()
            # L'utilisateur indique avoir produit X% du budget sur cette période. 
            # On le convertit en Euros, puis on l'ajoute au montant cumulé précédent.
            period_amount = (rec.target_project_revenue or 0.0) * (rec.progress_revenue_rate_period or 0.0)
            rec.progress_revenue_amount = (rec.rel_previous_progress_revenue_amount or 0.0) + period_amount
            # En modifiant progress_revenue_amount, Odoo déclenchera tout seul '_inverse_revenue' 
            # qui mettra à jour le taux d'avancement cumulé (progress_revenue_rate).

    # --- progress_cost_amount_period ---
    @api.depends('progress_cost_amount', 'rel_previous_progress_cost_amount')
    def _compute_progress_cost_amount_period(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_cost_amount_period = (rec.progress_cost_amount or 0.0) - (rec.rel_previous_progress_cost_amount or 0.0)

    # --- progress_revenue_amount_period ---
    @api.depends('progress_revenue_amount', 'rel_previous_progress_revenue_amount')
    def _compute_progress_revenue_amount_period(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_revenue_amount_period = (rec.progress_revenue_amount or 0.0) - (rec.rel_previous_progress_revenue_amount or 0.0)

    @api.depends('progress_revenue_amount_period', 'progress_cost_amount_period')
    def _compute_progress_revenue_margin_period(self):
        for rec in self:
            rec._check_can_write()
            rec.progress_revenue_margin_period = (rec.progress_revenue_amount_period or 0.0) - (rec.progress_cost_amount_period or 0.0)

    # --- progress_revenue_margin_rate_period ---
    @api.depends('progress_revenue_margin_period', 'progress_revenue_amount_period')
    def _compute_progress_revenue_margin_rate_period(self):
        for rec in self:
            rec._check_can_write()
            if rec.progress_revenue_amount_period:
                rec.progress_revenue_margin_rate_period = (rec.progress_revenue_margin_period or 0.0) / rec.progress_revenue_amount_period
            else:
                rec.progress_revenue_margin_rate_period = 0.0

    # --- future_staffing_days ---
    @api.depends('type', 'rel_project_id', 'rel_closing_date')
    def _compute_future_staffing_days(self):
        for rec in self:
            rec._check_can_write()
            if rec.type == 'internal_production' and rec.rel_project_id and rec.rel_closing_date:
                # TODO : sur Napta, les périodes de forecast sont découpées à la semaine, sauf pour les fin de mois.
                # Donc si le jour de clôture est en cours de semaine, alors il manquera des jours !
                lines = rec.rel_project_id.get_production_cost(
                    [('date', '>', rec.rel_closing_date), ('category', '=', 'project_forecast')],
                    force_recompute_amount=False)[1]
                rec.future_staffing_days = sum(line['unit_amount'] for line in lines)
            else:
                rec.future_staffing_days = 0.0

    # --- price_unit ---
    @api.depends('target_project_cost', 'target_project_outsourcing_product_qty')
    def _compute_price_unit(self):
        for rec in self:
            rec._check_can_write()
            rec.price_unit = ((rec.target_project_cost or 0.0) / rec.target_project_outsourcing_product_qty) if rec.target_project_outsourcing_product_qty else 0.0

    # --- reselling_price_unit ---
    @api.depends('target_project_revenue', 'target_project_outsourcing_product_qty')
    def _compute_reselling_price_unit(self):
        for rec in self:
            rec._check_can_write()
            rec.reselling_price_unit = ((rec.target_project_revenue or 0.0) / rec.target_project_outsourcing_product_qty) if rec.target_project_outsourcing_product_qty else 0.0

    # --- purchase_period_amount ---
    @api.depends('outsourcing_link_id', 'rel_project_id', 'rel_closing_date', 'accounting_closing_id.previous_closing')
    def _compute_purchase_period_amount(self):
        for rec in self:
            rec._check_can_write()
            if not rec.outsourcing_link_id:
                rec.purchase_period_amount = 0.0
                continue
            
            previous_closing = rec.accounting_closing_id.previous_closing
            domain = [
                ('partner_id', '=', rec.outsourcing_link_id.partner_id.id),
                ('date', '<=', rec.rel_closing_date),
                ('parent_state', 'in', ['posted']),
                ('move_type', 'in', ['in_refund', 'in_invoice'])
            ]
            if previous_closing:
                domain.append(('date', '>', previous_closing.closing_date))
            
            subtotal, total, paid, line_ids = rec.rel_project_id.compute_account_move_total_all_partners(domain)
            rec.purchase_period_amount = -1 * subtotal

    # --- Provisions (CCA / FNP) ---
    @api.depends('previous_progress_id.cca_balance')
    def _compute_cca_previous_balance(self):
        for rec in self:
            rec._check_can_write()
            rec.cca_previous_balance = rec.previous_progress_id.cca_balance if rec.previous_progress_id else 0.0

    @api.depends('previous_progress_id.fnp_balance')
    def _compute_fnp_previous_balance(self):
        for rec in self:
            rec._check_can_write()
            rec.fnp_previous_balance = rec.previous_progress_id.fnp_balance if rec.previous_progress_id else 0.0

    @api.depends('progress_cost_amount', 'rel_closing_date', 'outsourcing_link_id', 'auto_compute_provisions')
    def _compute_provisions_balances(self):
        for rec in self:
            if not rec.auto_compute_provisions:
                return
            rec._check_can_write()
            if not rec.outsourcing_link_id:
                rec.cca_balance = 0.0
                rec.fnp_balance = 0.0
                continue
            
            domain = [
                ('partner_id', '=', rec.outsourcing_link_id.partner_id.id),
                ('date', '<=', rec.rel_closing_date),
                ('parent_state', 'in', ['posted']),
                ('move_type', 'in', ['in_refund', 'in_invoice'])
            ]
            subtotal, total, paid, line_ids = rec.rel_project_id.compute_account_move_total_all_partners(domain)
            cumul_real = -1 * subtotal
            
            cost_gap = rec.progress_cost_amount - cumul_real
            
            if cost_gap < 0:
                rec.cca_balance = -cost_gap
                rec.fnp_balance = 0.0
            else:
                rec.cca_balance = 0.0
                rec.fnp_balance = -cost_gap

    @api.depends('cca_balance', 'cca_previous_balance')
    def _compute_cca_period_amount(self):
        for rec in self:
            rec._check_can_write()
            rec.cca_period_amount = rec.cca_balance - rec.cca_previous_balance

    @api.depends('fnp_balance', 'fnp_previous_balance')
    def _compute_fnp_period_amount(self):
        for rec in self:
            rec._check_can_write()
            rec.fnp_period_amount = rec.fnp_balance - rec.fnp_previous_balance

    # ===================================================================
    # ONCHANGE (Ponts de réactivité IHM)
    # Les inverses ne tournant qu'au save, ces onchanges permettent de 
    # synchroniser l'IHM en temps réel pendant la saisie (lorsque l'usager tabule, 
    # il voit le résultat sans attendre de sortir de la carte pour déclencher 
    # l'auto-save ou de cliquer surle bouton enregistrer)
    # ===================================================================
    @api.onchange('progress_revenue_rate')
    def _onchange_progress_revenue_rate(self):
        self._inverse_progress_revenue_rate()

    @api.onchange('outsourcing_product_qty_period')
    def _onchange_qty_period(self):
        self._inverse_qty_period()

    @api.onchange('progress_revenue_rate_period')
    def _onchange_progress_revenue_rate_period(self):
        self._inverse_progress_revenue_rate_period()

    @api.onchange('progress_revenue_amount')
    def _onchange_progress_revenue_amount(self):
        self._inverse_revenue()

    @api.onchange('outsourcing_product_qty')
    def _onchange_outsourcing_product_qty(self):
        self._inverse_outsourcing_product_qty()

    # ===================================================================
    # ACTIONS
    # ===================================================================
    def goto_napta(self):
        self.ensure_one()
        return self.accounting_closing_id.goto_napta()

    def action_validate(self):
        self.ensure_one()
        self.write({'is_validated': True})

    def action_invalidate(self):
        self.ensure_one()
        self.write({'is_validated': False})
                   

    def force_refresh(self):
        """Force le recalcul de toutes les données (écrase les saisies manuelles)."""
        _logger.info("================= force_refresh")
        for rec in self:
            #mise à jour manuelle du CA cible, notamment lorsque Margaux/le DM crée les BCC après la génération initiale de l'avancement
            rec._compute_progress_cost_amount()
            rec._compute_target_project_cost()
            rec._compute_target_project_outsourcing_product_qty()
            rec._compute_outsourcing_product_qty()
            rec._compute_qty_period()
            rec._compute_progress_cost_amount()
            rec._compute_progress_revenue_rate()
            rec._compute_progress_revenue_amount()
            rec._compute_progress_revenue_rate()
            rec._compute_progress_revenue_rate_period()
            rec._compute_progress_cost_amount_period()
            rec._compute_progress_revenue_amount_period()
            rec._compute_future_staffing_days()
            rec._compute_price_unit()
            rec._compute_reselling_price_unit()
            rec._compute_provisions_balances()
            rec._compute_target_project_revenue()



    # ===================================================================
    # CONTRAINTES
    # ===================================================================
    """
    @api.constrains('progress_revenue_amount', 'target_project_revenue')
    def _check_progress_revenue_amount(self):
        for rec in self:
            if rec.target_project_revenue and round(rec.progress_revenue_amount, 2) > round(rec.target_project_revenue, 2):
                raise ValidationError(_(
                    "La valorisation de l'avancement en prix de vente (%(amount)s) ne peut pas dépasser "
                    "le prix de vente total projeté (%(target)s) [projet = %(project)s et type = %(type)s].",
                    amount=rec.progress_revenue_amount,
                    target=rec.target_project_revenue,
                    project=rec.rel_project_id.number,
                    type=rec.type
                ))
    """

    @api.constrains('outsourcing_link_id', 'accounting_closing_id')
    def _check_project_consistency(self):
        for rec in self:
            if rec.outsourcing_link_id and rec.accounting_closing_id:
                link_project_id = rec.outsourcing_link_id.project_id.id
                closing_project_id = rec.accounting_closing_id.project_id.id
                if link_project_id and closing_project_id and link_project_id != closing_project_id:
                    raise ValidationError(_("Le lien de sous-traitance (%s) doit appartenir au même projet que la clôture (%s).") % (rec.outsourcing_link_id.project_id.name, rec.accounting_closing_id.project_id.name))
