from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .project_outsourcing_link import OUTSOURCING_LINK_TYPES

class ProjectProgress(models.Model):
    _name = 'project.progress'
    _description = 'Avancement Projet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rel_closing_date desc, id desc'

    _sql_constraints = [
        ('unique_closing_link', 'UNIQUE(accounting_closing_id, outsourcing_link_id)', 
         'Il ne peut y avoir qu\'un seul avancement par couple clôture / lien de sous-traitance.')
    ]

    accounting_closing_id = fields.Many2one('project.accounting_closing', string="Clôture comptable", required=True, ondelete='restrict')
    rel_closing_date = fields.Date(related='accounting_closing_id.closing_date', string="Date de clôture", store=True)
    outsourcing_link_id = fields.Many2one('project.outsourcing.link', string="Lien projet / fournisseur", store=True)
    rel_project_id = fields.Many2one('project.project', related='accounting_closing_id.project_id', string="Projet", store=True)
    rel_project_user_id = fields.Many2one(related='rel_project_id.user_id', string="Directeur de mission", store=True)
    rel_project_manager_user_id = fields.Many2one(related='rel_project_id.project_manager.user_id', string="Partner ou manager en appui", store=True)
    
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Devise", readonly=True)

    type = fields.Selection([('internal_production', 'Production interne')] + OUTSOURCING_LINK_TYPES, 
                            string="Type", compute='compute', store=True)

    previous_progress_id = fields.Many2one('project.progress', string="Avancement précédent", 
                                          compute='compute', store=True)
    next_progress = fields.Many2one('project.progress', string="Avancement suivant", compute='compute', store=True)

    rel_previous_progress_rate = fields.Float(related='previous_progress_id.progress_rate', string="Taux d'avancement précédent")
    rel_previous_progress_cost_amount = fields.Monetary(related='previous_progress_id.progress_cost_amount', string="Coût de revient précédent")
    rel_previous_progress_revenue_amount = fields.Monetary(related='previous_progress_id.progress_revenue_amount', string="Prix de vente précédent")

    target_project_cost = fields.Monetary(string="Coût de revient total projeté", compute='compute', store=True)
    target_project_revenue = fields.Monetary(string="Prix de vente de revient total projeté", compute='compute', store=True)

    progress_rate = fields.Float(string="Part des livrables terminés")

    progress_cost_amount = fields.Monetary(string="Valorisation de l’avancement en coût de revient", 
                                          compute='compute', store=True)
    progress_revenue_amount = fields.Monetary(string="Valorisation de l’avancement en prix de vente", 
                                             compute='compute', store=True)

    is_validated = fields.Boolean(string="Validé", tracking=True)

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

    def write(self, vals):
        for rec in self:
            if rec.next_progress:
                raise ValidationError(_("Il n'est pas possible de modifier cet avancement car un avancement postérieur existe."))
            if rec.is_validated:
                for val_key in vals.keys():
                    if val_key not in ['is_validated', 'message_follower_ids', 'message_ids', 'activity_ids', 'message_attachment_ids', 'message_main_attachment_id']:
                        raise ValidationError(_("Il n'est pas possible de modifier cet avancement car il est validé.\n\nTentative de modification de l'attribut : %s") % val_key)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.next_progress:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car un avancement postérieur existe."))
            if rec.is_validated:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car il est validé."))
        return super().unlink()

    @api.depends('accounting_closing_id', 'accounting_closing_id.previous_closing', 'outsourcing_link_id', 
                 'progress_rate', 'is_validated', 'accounting_closing_id.production_period_amount',
                 'rel_project_id.company_part_cost_current', 'rel_project_id.company_part_cost_futur', 
                 'rel_project_id.company_part_amount_current')
    def compute(self):
        for rec in self:
            # 1. Type
            if rec.outsourcing_link_id:
                rec.type = rec.outsourcing_link_id.link_type
            else:
                rec.type = 'internal_production'

            # 2. Previous Progress logic
            previous_closing = rec.accounting_closing_id.previous_closing
            if previous_closing:
                rec.previous_progress_id = self.env['project.progress'].search([
                    ('accounting_closing_id', '=', previous_closing.id),
                    ('outsourcing_link_id', '=', rec.outsourcing_link_id.id)
                ], limit=1)
            else:
                rec.previous_progress_id = False

            # 3. Target amounts
            if rec.type == 'internal_production':
                rec.target_project_cost = (rec.rel_project_id.company_part_cost_current or 0.0) + (rec.rel_project_id.company_part_cost_futur or 0.0)
                rec.target_project_revenue = rec.rel_project_id.company_part_amount_current or 0.0
            elif rec.outsourcing_link_id:
                rec.target_project_cost = rec.outsourcing_link_id.order_sum_purchase_order_lines or 0.0
                rec.target_project_revenue = rec.outsourcing_link_id.outsource_part_amount_current or 0.0
            else:
                rec.target_project_cost = 0.0
                rec.target_project_revenue = 0.0

            # 4. Progress amounts
            if rec.type == 'internal_production':
                rec.progress_cost_amount = rec.accounting_closing_id.production_period_amount or 0.0
            else:
                rec.progress_cost_amount = (rec.target_project_cost or 0.0) * (rec.progress_rate or 0.0)
            rec.progress_revenue_amount = (rec.target_project_revenue or 0.0) * (rec.progress_rate or 0.0)

            # 5. Next Progress logic (inspired by project.accounting_closing)
            next_progress = self.env['project.progress'].search([('previous_progress_id', '=', rec.id)], limit=1)
            rec.next_progress = next_progress
            if next_progress:
                next_progress.compute()

    @api.constrains('outsourcing_link_id', 'accounting_closing_id')
    def _check_project_consistency(self):
        for rec in self:
            if rec.outsourcing_link_id and rec.outsourcing_link_id.project_id != rec.rel_project_id.id:
                raise ValidationError("Le lien de sous-traitance doit appartenir au même projet que la clôture.")
