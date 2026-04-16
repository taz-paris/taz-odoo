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
        ('unique_closing_link', 'UNIQUE(accounting_closing_id, outsourcing_link_id)', 
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
    
    company_id = fields.Many2one('res.company', string='Société', required=True, related="accounting_closing_id.company_id")
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Devise", readonly=True)

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

    # --- Quantités S/T ---
    target_project_outsourcing_product_qty = fields.Float(string="Nb unités commandées", compute='_compute_target_project_outsourcing_product_qty', store=True)
    outsourcing_product_qty = fields.Float(string="Nb unités produites", store=True, readonly=False)
    outsourcing_product_qty_period = fields.Float(string="Nb unités produites période", compute='_compute_qty_period', inverse='_inverse_qty_period', store=True, readonly=False)

    # --- Avancement cumulé ---
    progress_cost_amount = fields.Monetary(string="Coût de revient", compute='_compute_progress_cost_amount', store=True)
    progress_revenue_rate = fields.Float(string="CA cumulé en %", aggregator=False, compute='_compute_progress_revenue_rate', inverse='_inverse_progress_revenue_rate', store=True, readonly=False)
    progress_revenue_amount = fields.Monetary(string="CA cumulé en €", 
                                             compute='_compute_progress_revenue_amount', inverse='_inverse_revenue', store=True, readonly=False)
    progress_revenue_margin = fields.Monetary(string="Marge en €", 
                                             compute='_compute_progress_revenue_margin', store=True)
    progress_revenue_margin_rate = fields.Float(string="Marge en %", aggregator=False,
                                             compute='_compute_progress_revenue_margin_rate', store=True)
    # --- Avancement période ---
    progress_cost_amount_period = fields.Monetary(string="Coût de revient période", 
                                                 compute='_compute_progress_cost_amount_period', store=True)
    progress_revenue_rate_period = fields.Float(string="CA période en % du prix de vente", aggregator=False, compute='_compute_progress_revenue_rate_period', inverse='_inverse_progress_revenue_rate_period', store=True, readonly=False)
    progress_revenue_amount_period = fields.Monetary(string="CA période en €", 
                                                    compute='_compute_progress_revenue_amount_period', store=True)

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
            if rec.accounting_closing_id.is_validated:
                raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est lié à une clôture validée."))
            if rec.next_progress:
                raise ValidationError(_("Il n'est pas possible de modifier cet avancement car un avancement postérieur existe."))
            if rec.is_validated:
                for val_key in vals.keys():
                    if val_key not in ['is_validated', 'message_follower_ids', 'message_ids', 'activity_ids', 'message_attachment_ids', 'message_main_attachment_id']:
                        raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est validé.\n\nTentative de modification de l'attribut : %s") % val_key)
        
        res = super().write(vals)

        return res

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
            rec.type = rec.outsourcing_link_id.link_type if rec.outsourcing_link_id else 'internal_production'

    # --- previous_progress_id ---
    @api.depends('accounting_closing_id', 'accounting_closing_id.previous_closing', 'outsourcing_link_id')
    def _compute_previous_progress_id(self):
        for rec in self:
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
            rec.next_progress = self.env['project.progress'].search([('previous_progress_id', '=', rec.id)], limit=1)

    # --- target_project_cost ---
    # Dépend uniquement de type et outsourcing_link_id (positionnés à la création).
    # Pas de dépendance sur rel_project_id.company_part_* pour éviter l'écrasement
    # des valeurs lorsque les données du projet changent a posteriori.
    @api.depends('type', 'outsourcing_link_id')
    def _compute_target_project_cost(self):
        for rec in self:
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


    # --- target_project_outsourcing_product_qty ---
    @api.depends('outsourcing_link_id.order_sum_purchase_order_product_qty')
    def _compute_target_project_outsourcing_product_qty(self):
        #TODO : attention, cette zone va etre recalculée lorsque l'on change la qté sur le BCF => ça va bloquer margaux car ça sera interdit post validation
        for rec in self:
            rec.target_project_outsourcing_product_qty = rec.outsourcing_link_id.order_sum_purchase_order_product_qty if rec.outsourcing_link_id else 0.0

    # --- outsourcing_product_qty_period ---
    @api.depends('outsourcing_product_qty', 'previous_progress_id.outsourcing_product_qty')
    def _compute_qty_period(self):
        for rec in self:
            rec.outsourcing_product_qty_period = (rec.outsourcing_product_qty or 0.0) - (rec.previous_progress_id.outsourcing_product_qty or 0.0)

    def _inverse_qty_period(self):
        for rec in self:
            rec.outsourcing_product_qty = (rec.previous_progress_id.outsourcing_product_qty or 0.0) + (rec.outsourcing_product_qty_period or 0.0)

    # --- progress_cost_amount ---
    # Pour outsourcing : formule directe (cost * qty/target_qty) au lieu de cost * rate
    # afin d'éviter une dépendance circulaire avec progress_revenue_rate
    @api.depends('type', 'rel_project_id', 'rel_closing_date',
                 'target_project_cost', 'outsourcing_product_qty', 'target_project_outsourcing_product_qty')
    def _compute_progress_cost_amount(self):
        for rec in self:
            if rec.type == 'internal_production':
                rec.progress_cost_amount = -rec.rel_project_id.get_production_cost(
                    [('date', '<=', rec.rel_closing_date), ('category', '=', 'project_employee_validated')],
                    force_recompute_amount=False)[0]
            elif rec.outsourcing_link_id:
                if rec.type == 'other':
                    purchase_period_subtotal, purchase_period_total, purchase_period_paid, purchase_period_line_ids = rec.rel_project_id.compute_account_move_total_all_partners([('partner_id', '=', rec.outsourcing_link_id.partner_id.id), ('date', '<=', rec.rel_closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['in_refund', 'in_invoice'])])
                    rec.progress_cost_amount = -1 * purchase_period_subtotal
                else :
                    target_qty = rec.target_project_outsourcing_product_qty or 0.0
                    rate = (rec.outsourcing_product_qty / target_qty) if target_qty else 0.0
                    rec.progress_cost_amount = (rec.target_project_cost or 0.0) * rate
            else:
                rec.progress_cost_amount = 0.0

    # --- progress_revenue_rate ---
    @api.depends('progress_cost_amount', 'target_project_cost')
    def _compute_progress_revenue_rate(self):
        for rec in self:
            rec.progress_revenue_rate = (rec.progress_cost_amount / rec.target_project_cost) if rec.target_project_cost else 0.0

    def _inverse_progress_revenue_rate(self):
        for rec in self:
            if not rec.progress_revenue_rate:
                continue
            if rec.type == 'internal_production':
                pass  # Asymétrie : ne pas remonter vers le target_project_cost
            elif rec.target_project_outsourcing_product_qty:
                rec.outsourcing_product_qty = rec.progress_revenue_rate * rec.target_project_outsourcing_product_qty

    # --- progress_revenue_amount ---
    @api.depends('target_project_revenue', 'progress_revenue_rate')
    def _compute_progress_revenue_amount(self):
        for rec in self:
            rec.progress_revenue_amount = (rec.target_project_revenue or 0.0) * (rec.progress_revenue_rate or 0.0)

    def _inverse_revenue(self):
        for rec in self:
            rate = (rec.progress_revenue_amount / rec.target_project_revenue) if rec.target_project_revenue else 0.0
            if rec.type == 'internal_production':
                rec.progress_revenue_rate = rate
            else:
                rec.outsourcing_product_qty = rate * rec.target_project_outsourcing_product_qty

    # --- progress_revenue_margin ---
    @api.depends('progress_revenue_amount', 'progress_cost_amount')
    def _compute_progress_revenue_margin(self):
        for rec in self:
            rec.progress_revenue_margin = (rec.progress_revenue_amount or 0.0) - (rec.progress_cost_amount or 0.0)    
    
    # --- progress_revenue_margin_rate ---
    @api.depends('progress_revenue_margin', 'progress_revenue_amount')
    def _compute_progress_revenue_margin_rate(self):
        for rec in self:
            if rec.progress_revenue_amount:
                rec.progress_revenue_margin_rate = (rec.progress_revenue_margin or 0.0) / rec.progress_revenue_amount
            else:
                rec.progress_revenue_margin_rate = 0.0
    
    # --- progress_revenue_rate_period ---
    @api.depends('progress_revenue_rate', 'rel_previous_progress_revenue_rate')
    def _compute_progress_revenue_rate_period(self):
        for rec in self:
            rec.progress_revenue_rate_period = (rec.progress_revenue_rate or 0.0) - (rec.rel_previous_progress_revenue_rate or 0.0)

    def _inverse_progress_revenue_rate_period(self):
        for rec in self:
            new_rate = (rec.rel_previous_progress_revenue_rate or 0.0) + (rec.progress_revenue_rate_period or 0.0)
            if rec.type == 'internal_production':
                rec.progress_revenue_rate = new_rate
            else:
                rec.outsourcing_product_qty = new_rate * rec.target_project_outsourcing_product_qty

    # --- progress_cost_amount_period ---
    @api.depends('progress_cost_amount', 'rel_previous_progress_cost_amount')
    def _compute_progress_cost_amount_period(self):
        for rec in self:
            rec.progress_cost_amount_period = (rec.progress_cost_amount or 0.0) - (rec.rel_previous_progress_cost_amount or 0.0)

    # --- progress_revenue_amount_period ---
    @api.depends('progress_revenue_amount', 'rel_previous_progress_revenue_amount')
    def _compute_progress_revenue_amount_period(self):
        for rec in self:
            rec.progress_revenue_amount_period = (rec.progress_revenue_amount or 0.0) - (rec.rel_previous_progress_revenue_amount or 0.0)

    # --- future_staffing_days ---
    @api.depends('type', 'rel_project_id', 'rel_closing_date')
    def _compute_future_staffing_days(self):
        for rec in self:
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
            rec.price_unit = ((rec.target_project_cost or 0.0) / rec.target_project_outsourcing_product_qty) if rec.target_project_outsourcing_product_qty else 0.0

    # --- reselling_price_unit ---
    @api.depends('target_project_revenue', 'target_project_outsourcing_product_qty')
    def _compute_reselling_price_unit(self):
        for rec in self:
            rec.reselling_price_unit = ((rec.target_project_revenue or 0.0) / rec.target_project_outsourcing_product_qty) if rec.target_project_outsourcing_product_qty else 0.0

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


    def data_init_2026(self):
        cumuls_31_12_2025 = {
'99TS005' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 30609.92, 'ca_autre' : 0},
'99TS004' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'99TS003' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 21422.22, 'ca_autre' : 0},
'99TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 37245, 'ca_autre' : 0},
'99TS001' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 12164.76, 'ca_autre' : 0},
'26TS085' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS084' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS083' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS082' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS081' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS080' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS079' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS078' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS077' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS076' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS075' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS074' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS073' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS072' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS071' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS070' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS069' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS068' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS067' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS066' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS065' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS064' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS063' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS062' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS061' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS060' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS059' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS058' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS057' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS056' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS055' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS054' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS053' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS052' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS051' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS050' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS049' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS048' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS047' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS046' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS045' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS044' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS043' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS042' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS041' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS038' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS037' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS031' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS029' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS028' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS027' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS026' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS017' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS016' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS015' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS014' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS013' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS012' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS011' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS010' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS009' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS008' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS007' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS001' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS379' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS376' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS374' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS373' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS372' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS371' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS370' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS369' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS368' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS367' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS365' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS364' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS363' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS362' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS361' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS359' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS358' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS357' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS356' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS355' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS354' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS353' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS352' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS351' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS350' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS345' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS344' : {'internal' : 16172.25, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS343' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS340' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS339' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS338' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS333' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS332' : {'internal' : 6400, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS331' : {'internal' : 11084.43, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS330' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS329' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS328' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS327' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS326' : {'internal' : 4519.88, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 33.58},
'25TS325' : {'internal' : 14486.04, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS323' : {'internal' : 2005.25, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS322' : {'internal' : 7.27595761418343E-12, 'ogures' : 95606.65, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 50553.35, 'prestation' : 0, 'ca_autre' : 0},
'25TS321' : {'internal' : 9414.01, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS320' : {'internal' : 1473.65, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS319' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS318' : {'internal' : 15396, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS317' : {'internal' : 34670, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS316' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS315' : {'internal' : 7540.66, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 534.34},
'25TS311' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS310' : {'internal' : 85000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS309' : {'internal' : 4985, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS308' : {'internal' : 7949.4, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 1380, 'prestation' : 0, 'ca_autre' : 70.6},
'25TS307' : {'internal' : 25910, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 95},
'25TS306' : {'internal' : 120309.72, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 2600, 'prestation' : 0, 'ca_autre' : 341},
'25TS303' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS300' : {'internal' : 1561.7, 'ogures' : 36908, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 245.3},
'25TS299' : {'internal' : 50000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS298' : {'internal' : 4000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS297' : {'internal' : 16000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS295' : {'internal' : 26000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS294' : {'internal' : 62130, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS293' : {'internal' : 8091.88, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 102.72},
'25TS292' : {'internal' : 53982.31, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 1976.59},
'25TS291' : {'internal' : -2.91038304567337E-11, 'ogures' : 34311.8, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 185829.6, 'prestation' : 0, 'ca_autre' : 0},
'25TS290' : {'internal' : 21156.5, 'ogures' : 23000, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS288' : {'internal' : 19421.04, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 28.96},
'25TS287' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS285' : {'internal' : 46300, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS284' : {'internal' : 56414.23, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 1865.77},
'25TS283' : {'internal' : 33000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS282' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS281' : {'internal' : 22086, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 519.48},
'25TS280' : {'internal' : 48100, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS277' : {'internal' : 29529.11, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 51980, 'prestation' : 0, 'ca_autre' : 48.89},
'25TS276' : {'internal' : 125500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 21000, 'prestation' : 0, 'ca_autre' : 0},
'25TS275' : {'internal' : 20609.62, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 390.38},
'25TS274' : {'internal' : 106090, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 28670, 'prestation' : 0, 'ca_autre' : 0},
'25TS273' : {'internal' : 33500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS272' : {'internal' : 34166.2, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS271' : {'internal' : 44770, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS270' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS269' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS268' : {'internal' : 21750, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS267' : {'internal' : 694.01, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS266' : {'internal' : 4286.3, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 69.45},
'25TS264' : {'internal' : 249336.31, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 373.69},
'25TS263' : {'internal' : 16000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS262' : {'internal' : 103345, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS261' : {'internal' : 63083.06, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 61.94},
'25TS257' : {'internal' : 37000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS256' : {'internal' : 16387.8, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS255' : {'internal' : 22960, 'ogures' : 94500, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS254' : {'internal' : 21875, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS253' : {'internal' : 38894.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 25100, 'prestation' : 0, 'ca_autre' : 105.5},
'25TS252' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 4500, 'prestation' : 0, 'ca_autre' : 0},
'25TS251' : {'internal' : 91323.3, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 76.7},
'25TS250' : {'internal' : 11520, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS249' : {'internal' : 33631.07, 'ogures' : 126738.93, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 125400, 'prestation' : 0, 'ca_autre' : 0},
'25TS248' : {'internal' : 167388.5, 'ogures' : 108766.5, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 170400, 'prestation' : 0, 'ca_autre' : 0},
'25TS247' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 195120, 'prestation' : 0, 'ca_autre' : 0},
'25TS244' : {'internal' : 23996.06, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 533.94},
'25TS242' : {'internal' : 231828, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 88850, 'prestation' : 0, 'ca_autre' : 896.05},
'25TS241' : {'internal' : 20267.5, 'ogures' : 44682.5, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS240' : {'internal' : 26692.98, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 3852.48},
'25TS238' : {'internal' : 69266, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS228' : {'internal' : 199955.06, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 44.94},
'25TS225' : {'internal' : 39800, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS219' : {'internal' : 106000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS218' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 245000, 'prestation' : 0, 'ca_autre' : 0},
'25TS216' : {'internal' : 105289.68, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS206' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS204' : {'internal' : 108852.18, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 17209.16, 'prestation' : 0, 'ca_autre' : 1188.66},
'25TS203' : {'internal' : 128250, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 178.45},
'25TS197' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS196' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS195' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS174' : {'internal' : 27186.14, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 383.86},
'25TS173' : {'internal' : 0, 'ogures' : 132000, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS170' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS161' : {'internal' : 2250, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 2250, 'prestation' : 0, 'ca_autre' : 0},
'25TS151' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS148' : {'internal' : 0, 'ogures' : 150000, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS142' : {'internal' : 7696.52, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 6163.48, 'prestation' : 0, 'ca_autre' : 0},
'25TS141' : {'internal' : 133848, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS137' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS136' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS134' : {'internal' : -489.54, 'ogures' : 393602.87, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 157682.13, 'prestation' : 0, 'ca_autre' : 489.54},
'25TS131' : {'internal' : 60390, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 759.96},
'25TS130' : {'internal' : 48770.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 9.5},
'25TS126' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS121' : {'internal' : 56473.44, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 1000, 'prestation' : 0, 'ca_autre' : 276.56},
'25TS120' : {'internal' : 147706.93, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 4601.98},
'25TS115' : {'internal' : 97267.2, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 240.2},
'25TS114' : {'internal' : 5227.5, 'ogures' : 41535, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS095' : {'internal' : 90326.8, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 2014.33},
'25TS091' : {'internal' : 250375.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 124.5},
'25TS082' : {'internal' : 25000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS079' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 12000, 'prestation' : 0, 'ca_autre' : 0},
'25TS016' : {'internal' : 83947.24, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 127.09},
'25TS002' : {'internal' : 56500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS377' : {'internal' : 91410, 'ogures' : 0, 'mc2i' : 28000, 'inditto' : 0, 'autre_ST' : 30590, 'prestation' : 0, 'ca_autre' : 0},
'24TS359' : {'internal' : 100000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS357' : {'internal' : 259026.42, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 4090.58},
'24TS184' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS023' : {'internal' : 84645.05, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 13000, 'prestation' : 0, 'ca_autre' : 2850.95},
'23294' : {'internal' : 13900, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
            }

        ca_periode_01_2026 = {
'99TS005' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 1884.94, 'ca_autre' : 0},
'99TS004' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'99TS003' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : -1500, 'ca_autre' : 0},
'99TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'99TS001' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 73.4, 'ca_autre' : 0},
'26TS085' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS084' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS083' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS082' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS081' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS080' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS079' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS078' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS077' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS076' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS075' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS074' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS073' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS072' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS071' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS070' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS069' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS068' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS067' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS066' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS065' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS064' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS063' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS062' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS061' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS060' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS059' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS058' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS057' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS056' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS055' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS054' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS053' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS052' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS051' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS050' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS049' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS048' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS047' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS046' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS045' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS044' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS043' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS042' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS041' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS038' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS037' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS031' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS029' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS028' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS027' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS026' : {'internal' : 1764.7, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS017' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS016' : {'internal' : 7000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS015' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS014' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS013' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS012' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS011' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS010' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS009' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS008' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 3600, 'prestation' : 0, 'ca_autre' : 0},
'26TS007' : {'internal' : 2000, 'ogures' : 17800, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 11400, 'prestation' : 0, 'ca_autre' : 0},
'26TS001' : {'internal' : 0, 'ogures' : 20400, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS379' : {'internal' : 19409.09, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS376' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS374' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS373' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS372' : {'internal' : 11722.97, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS371' : {'internal' : 14555, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS370' : {'internal' : 9553.57, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS369' : {'internal' : 40000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS368' : {'internal' : 6900, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS367' : {'internal' : 18860.09, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 7475, 'prestation' : 0, 'ca_autre' : 564.91},
'25TS365' : {'internal' : 10000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS364' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS363' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS362' : {'internal' : 3162.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS361' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS359' : {'internal' : 36877.19, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS358' : {'internal' : 44889.83, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS357' : {'internal' : 33000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS356' : {'internal' : 18000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS355' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS354' : {'internal' : 32192.47, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 807.53},
'25TS353' : {'internal' : 6310.34, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS352' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS351' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS350' : {'internal' : 15684.93, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS345' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS344' : {'internal' : 23957.25, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS343' : {'internal' : 12375, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS340' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS339' : {'internal' : 37500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS338' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS333' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS332' : {'internal' : 14100, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS331' : {'internal' : 9000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS330' : {'internal' : 0, 'ogures' : 31355, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS329' : {'internal' : 22266.02, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 33.98},
'25TS328' : {'internal' : -1.02318153949454E-12, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 9223.38, 'prestation' : 0, 'ca_autre' : 176.62},
'25TS327' : {'internal' : 68500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS326' : {'internal' : 24525.7, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 229.25},
'25TS325' : {'internal' : 6480.88, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS323' : {'internal' : 50887, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 388},
'25TS322' : {'internal' : -2.27373675443232E-13, 'ogures' : -2747.22, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : -1277.78, 'prestation' : 0, 'ca_autre' : 0},
'25TS321' : {'internal' : 46300, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS320' : {'internal' : 3710.35, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS319' : {'internal' : 15200, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS318' : {'internal' : 5000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS317' : {'internal' : 11037.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS316' : {'internal' : 7.105427357601E-14, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 8948.83, 'prestation' : 0, 'ca_autre' : 51.17},
'25TS315' : {'internal' : 3592.84, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 707.16},
'25TS311' : {'internal' : 9212.9, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS310' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS309' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS308' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS307' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS306' : {'internal' : 61429, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 3571, 'prestation' : 0, 'ca_autre' : 0},
'25TS303' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS300' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS299' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS298' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS297' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS295' : {'internal' : 10600, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS294' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS293' : {'internal' : 16750, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS292' : {'internal' : 10000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS291' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS290' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS288' : {'internal' : -28.96, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 28.96},
'25TS287' : {'internal' : 24600, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS285' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS284' : {'internal' : 312.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS283' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS282' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS281' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS280' : {'internal' : 13900, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS277' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS276' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS275' : {'internal' : 3703.12, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS274' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS273' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS272' : {'internal' : 6500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS271' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS270' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS269' : {'internal' : 12250, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS268' : {'internal' : 24900, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS267' : {'internal' : 11400, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS266' : {'internal' : 14000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS264' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS263' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS262' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS261' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS257' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS256' : {'internal' : 4000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS255' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS254' : {'internal' : 10097, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 103},
'25TS253' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS252' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS251' : {'internal' : -16960, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS250' : {'internal' : 2300, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS249' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS248' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS247' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS244' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS242' : {'internal' : -13050, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 13050, 'prestation' : 0, 'ca_autre' : 0},
'25TS241' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS240' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS238' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS228' : {'internal' : 12160, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS225' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS219' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS218' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS216' : {'internal' : 20000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS206' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS204' : {'internal' : 59146.74, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 1653.26},
'25TS203' : {'internal' : -3375, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS197' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS196' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS195' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS174' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS173' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS170' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS161' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS151' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS148' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS142' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS141' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS137' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS136' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS134' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS131' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS130' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS126' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS121' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS120' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS115' : {'internal' : 192.6, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS114' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS095' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS091' : {'internal' : 21800, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS082' : {'internal' : 2200, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS079' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS016' : {'internal' : 813.56, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS002' : {'internal' : 2000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS377' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS359' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS357' : {'internal' : 26000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS184' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS023' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'23294' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
    }

        ca_periode_02_2026 = {
'99TS005' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 1884.94, 'ca_autre' : 0},
'99TS004' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'99TS003' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'99TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 4500, 'ca_autre' : 0},
'99TS001' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 1043.82, 'ca_autre' : 0},
'26TS106' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS105' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS104' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS103' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS102' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS101' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS100' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS099' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS098' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS097' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS096' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS094' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS093' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS092' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS091' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS090' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS089' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS088' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS087' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS085' : {'internal' : 400, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS084' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS083' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS082' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS081' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS080' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS079' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS078' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS075' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS074' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS073' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS072' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS071' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS070' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS069' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS068' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS067' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS066' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS065' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS064' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS063' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS062' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS061' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS060' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS059' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS058' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS057' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS056' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS055' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS054' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS053' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS052' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS051' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS050' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS049' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS048' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS047' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS046' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS045' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS044' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS043' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS042' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS041' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS038' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS037' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS031' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS029' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS028' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS027' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS026' : {'internal' : 11297.8, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS017' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS016' : {'internal' : 16083.33, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS015' : {'internal' : 22000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS014' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS013' : {'internal' : 12710, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS012' : {'internal' : 9000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS011' : {'internal' : 2680, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS010' : {'internal' : 41030, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS009' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS008' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'26TS007' : {'internal' : 30, 'ogures' : 31227.62, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 95462.38, 'prestation' : 0, 'ca_autre' : 0},
'26TS002' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 33050, 'prestation' : 0, 'ca_autre' : 0},
'26TS001' : {'internal' : 2479.52, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS379' : {'internal' : 19636.36, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS376' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 3680, 'prestation' : 0, 'ca_autre' : 0},
'25TS374' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS373' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS372' : {'internal' : 32939.19, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS371' : {'internal' : 4850, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS370' : {'internal' : 6821.43, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS369' : {'internal' : -20000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS368' : {'internal' : 8100, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS367' : {'internal' : 13700, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS365' : {'internal' : 27200, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS364' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS363' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS362' : {'internal' : 19781.25, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS361' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS359' : {'internal' : 36464.91, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS358' : {'internal' : 47855.93, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS357' : {'internal' : 25971.05, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 16800, 'prestation' : 0, 'ca_autre' : 228.95},
'25TS356' : {'internal' : 18920, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS355' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS354' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS353' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS352' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS351' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS350' : {'internal' : 15445.21, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS345' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS344' : {'internal' : 18640, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS343' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS340' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS339' : {'internal' : 40340, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS333' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS332' : {'internal' : 4135, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS331' : {'internal' : 10550, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS330' : {'internal' : 3.63797880709171E-12, 'ogures' : 50325.38, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 29674.62, 'prestation' : 0, 'ca_autre' : 0},
'25TS329' : {'internal' : 24357.88, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 562.12},
'25TS328' : {'internal' : 28120, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS327' : {'internal' : 37479.9, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 20.1},
'25TS326' : {'internal' : 4315, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS325' : {'internal' : 8700, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS323' : {'internal' : 62850, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS322' : {'internal' : 0, 'ogures' : 65412.32, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 34587.68, 'prestation' : 0, 'ca_autre' : 0},
'25TS321' : {'internal' : 47600, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS320' : {'internal' : 7791, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS319' : {'internal' : 14800, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS318' : {'internal' : 7164, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS317' : {'internal' : 18800, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS316' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS315' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS311' : {'internal' : 14551, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS307' : {'internal' : 7124.28, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 375.72},
'25TS306' : {'internal' : 26425, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 975, 'prestation' : 0, 'ca_autre' : 0},
'25TS303' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS300' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS299' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS298' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS295' : {'internal' : 3400, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS293' : {'internal' : 20856.58, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 93.42},
'25TS292' : {'internal' : 20053, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS291' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS290' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS288' : {'internal' : 19450, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS287' : {'internal' : 24000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS284' : {'internal' : -312.5, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS283' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS282' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS280' : {'internal' : 18000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS277' : {'internal' : -39400, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS275' : {'internal' : -421.87, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS272' : {'internal' : 999.8, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS270' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS269' : {'internal' : 17500, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS268' : {'internal' : -790, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS267' : {'internal' : 13150, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS266' : {'internal' : 14530.55, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 69.45},
'25TS264' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS256' : {'internal' : -2300, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS254' : {'internal' : 11675, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS253' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS251' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS244' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS240' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS238' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS228' : {'internal' : 56040, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS225' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS216' : {'internal' : 22000, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS206' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS204' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS196' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS195' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS174' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS170' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS161' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS142' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS141' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS137' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS136' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS134' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS131' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS130' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS126' : {'internal' : 2350, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS121' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS120' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS114' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS095' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS091' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS082' : {'internal' : 22800, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS016' : {'internal' : -813.56, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'25TS002' : {'internal' : 4518.95, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS377' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'24TS357' : {'internal' : 25585, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 655},
'24TS184' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
'23294' : {'internal' : 0, 'ogures' : 0, 'mc2i' : 0, 'inditto' : 0, 'autre_ST' : 0, 'prestation' : 0, 'ca_autre' : 0},
        }

        _logger.info("=========== DATA INITIALIZATION")

        if self.rel_closing_date == datetime.date(2025, 12, 31):
            _logger.info("========== Initialisation des cumuls au 31/12/2025 pour le projet %s" % self.rel_project_id.number)
            if self.rel_project_id.number not in cumuls_31_12_2025.keys():
                _logger.info("Ce projet n'est pas dans les données de Denis : %s" % self.rel_project_id.number)
            else:
                cumul_projet_31_12_2025 = cumuls_31_12_2025[self.rel_project_id.number]
                _logger.info(str(cumul_projet_31_12_2025))
                if self.type == 'internal_production' :
                    self.progress_revenue_amount = cumul_projet_31_12_2025['internal'] + cumul_projet_31_12_2025['prestation']
                elif self.type == 'other' :
                    # il n'y a que le fournisseur FOURNISSEUR FRAIS DIVERS pour les lignes de type other pour décmebre 25 / janvier 26 et février 26 => donc attribution directe
                    self.progress_revenue_amount = cumul_projet_31_12_2025['ca_autre']
                    #rate = (self.progress_revenue_amount / self.target_project_revenue) if self.target_project_revenue else 0.0
                    #self.outsourcing_product_qty = rate * self.target_project_outsourcing_product_qty
                elif self.type == 'outsourcing' :
                    p = self.env['project.progress'].search([('accounting_closing_id', '=', self.accounting_closing_id.id), ('type', '=', self.type)])
                    if len(p) != 1 and (cumul_projet_31_12_2025['ogures']!=0 or cumul_projet_31_12_2025['mc2i']!=0 or cumul_projet_31_12_2025['inditto']!=0 or cumul_projet_31_12_2025['autre_ST']!=0) :
                        _logger.info("Ce projet a plusieurs project.progress de type outsourcing : %s" % self.rel_project_id.number)
                    else :
                       self.progress_revenue_amount = cumul_projet_31_12_2025['ogures'] + cumul_projet_31_12_2025['mc2i'] + cumul_projet_31_12_2025['inditto'] + cumul_projet_31_12_2025['autre_ST']
                       #rate = (self.progress_revenue_amount / self.target_project_revenue) if self.target_project_revenue else 0.0
                       #self.outsourcing_product_qty = rate * self.target_project_outsourcing_product_qty
                else : 
                    _logger.info("Ce projet a un projet.progrss dont le type %s n'est pas pris en charge n'est pas géré : %s" % (self.type ,self.rel_project_id.numbe))
                        

        if self.rel_closing_date == datetime.date(2026, 1, 31):
            _logger.info("========== Initialisation des CA périodique du mois de janvier 2026 pour le projet %s" % self.rel_project_id.number)
            if self.rel_project_id.number not in ca_periode_01_2026.keys():
                _logger.info("Ce projet n'est pas dans les données de Denis : %s" % self.rel_project_id.number)
            else:
                data_ca_projet = ca_periode_01_2026[self.rel_project_id.number]
                _logger.info(str(data_ca_projet))
                if self.type == 'internal_production' :
                    #self.progress_revenue_amount_period = data_ca_projet['internal'] + data_ca_projet['prestation']
                    self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['internal'] + data_ca_projet['prestation']
                elif self.type == 'other' :
                    # il n'y a que le fournisseur FOURNISSEUR FRAIS DIVERS pour les lignes de type other pour décmebre 25 / janvier 26 et février 26 => donc attribution directe
                    #self.progress_revenue_amount_period = data_ca_projet['ca_autre']
                    self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['ca_autre']
                elif self.type == 'outsourcing' :
                    p = self.env['project.progress'].search([('accounting_closing_id', '=', self.accounting_closing_id.id), ('type', '=', self.type)])
                    if len(p) != 1 and (data_ca_projet['ogures']!=0 or data_ca_projet['mc2i']!=0 or data_ca_projet['inditto']!=0 or data_ca_projet['autre_ST']!= 0) :
                        _logger.info("Ce projet a plusieurs project.progress de type outsourcing : %s" % self.rel_project_id.number)
                    else :
                       #self.progress_revenue_amount_period = data_ca_projet['ogures'] + data_ca_projet['mc2i'] + data_ca_projet['inditto'] + data_ca_projet['autre_ST']
                       self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['mc2i'] + data_ca_projet['inditto'] + data_ca_projet['autre_ST']
                else : 
                    _logger.info("Ce projet a un projet.progrss dont le type %s n'est pas pris en charge n'est pas géré : %s" % (self.type ,self.rel_project_id.numbe))
                        
        if self.rel_closing_date == datetime.date(2026, 2, 28):
            _logger.info("========== Initialisation des CA périodique du mois de fevrier 2026 pour le projet %s" % self.rel_project_id.number)
            if self.rel_project_id.number not in ca_periode_02_2026.keys():
                _logger.info("Ce projet n'est pas dans les données de Denis : %s" % self.rel_project_id.number)
            else:
                data_ca_projet = ca_periode_02_2026[self.rel_project_id.number]
                _logger.info(str(data_ca_projet))
                if self.type == 'internal_production' :
                    #self.progress_revenue_amount_period = data_ca_projet['internal'] + data_ca_projet['prestation']
                    self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['internal'] + data_ca_projet['prestation']
                elif self.type == 'other' :
                    # il n'y a que le fournisseur FOURNISSEUR FRAIS DIVERS pour les lignes de type other pour décmebre 25 / janvier 26 et février 26 => donc attribution directe
                    #self.progress_revenue_amount_period = data_ca_projet['ca_autre']
                    self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['ca_autre']
                elif self.type == 'outsourcing' :
                    p = self.env['project.progress'].search([('accounting_closing_id', '=', self.accounting_closing_id.id), ('type', '=', self.type)])
                    if len(p) != 1 and (data_ca_projet['ogures']!=0 or data_ca_projet['mc2i']!=0 or data_ca_projet['inditto']!=0 or data_ca_projet['autre_ST']!= 0) :
                        _logger.info("Ce projet a plusieurs project.progress de type outsourcing : %s" % self.rel_project_id.number)
                    else :
                       #self.progress_revenue_amount_period = data_ca_projet['ogures'] + data_ca_projet['mc2i'] + data_ca_projet['inditto'] + data_ca_projet['autre_ST']
                       self.progress_revenue_amount = self.rel_previous_progress_revenue_amount + data_ca_projet['mc2i'] + data_ca_projet['inditto'] + data_ca_projet['autre_ST']
                else : 
                    _logger.info("Ce projet a un projet.progrss dont le type %s n'est pas pris en charge n'est pas géré : %s" % (self.type ,self.rel_project_id.numbe))
                        

    def force_refresh(self):
        """Force le recalcul de toutes les données (écrase les saisies manuelles)."""
        _logger.info("================= force_refresh")
        for rec in self:
            #mise à jour manuelle du CA cible, notamment lorsque Margaux/le DM crée les BCC après la génération initiale de l'avancement
            rec._compute_target_project_revenue()
            """
            rec.target_project_cost = 0.0
            rec.target_project_revenue = 0.0
            #rec._compute_type()
            #rec._compute_previous_progress_id()
            #rec._compute_next_progress()

            rec._compute_progress_cost_amount()
            rec._compute_target_project_cost()
            rec._compute_target_project_outsourcing_product_qty()
            rec._compute_qty_period()
            rec._compute_progress_cost_amount()
            rec._compute_progress_revenue_rate()
            rec._compute_progress_revenue_amount()
            rec._compute_progress_revenue_rate_period()
            rec._compute_progress_cost_amount_period()
            rec._compute_progress_revenue_amount_period()
            rec._compute_future_staffing_days()
            rec._compute_price_unit()
            rec._compute_reselling_price_unit()

            rec.data_init_2026()
            """


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
