from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .project_outsourcing_link import OUTSOURCING_LINK_TYPES

class ProjectProgress(models.Model):
    _name = 'project.progress'
    _description = 'Avancement Projet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rel_closing_date desc, type asc, id asc'

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
    rel_outsourcing_partner_id = fields.Many2one(related='outsourcing_link_id.partner_id', string="Fournisseur", store=True)
    
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

    target_project_outsourcing_product_qty = fields.Float(string="Nb unités commandées S/T", compute='compute', store=True)
    outsourcing_product_qty = fields.Float(string="Nb unités produites S/T", store=True, readonly=False)
    outsourcing_product_qty_period = fields.Float(string="Nb unités produites S/T période", compute='compute', inverse='_inverse_qty_period', store=True, readonly=False)

    progress_rate = fields.Float(string="Avancement à date de la clôture", inverse='_inverse_progress_rate')

    progress_cost_amount = fields.Monetary(string="Valorisation de l’avancement en coût de revient", compute='compute', store=True)
    progress_revenue_amount = fields.Monetary(string="Valorisation de l’avancement en prix de vente", 
                                             compute='compute', inverse='_inverse_revenue', store=True, readonly=False)
    progress_rate_period = fields.Float(string="Avancement sur la période (en points)", compute='compute', inverse='_inverse_progress_rate_period', store=True, readonly=False)
    progress_cost_amount_period = fields.Monetary(string="Variation de l’avancement en coût de revient sur la période", 
                                                 compute='compute', store=True)
    progress_revenue_amount_period = fields.Monetary(string="Variation de l’avancement en prix de vente sur la période", 
                                                    compute='compute', inverse='_inverse_revenue_period', store=True, readonly=False)

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
        
        res = super().write(vals)
        
        # Si on dévalide un avancement, on dévalide automatiquement la clôture liée
        if 'is_validated' in vals and not vals.get('is_validated'):
            for rec in self:
                if rec.accounting_closing_id.is_validated:
                    rec.accounting_closing_id.is_validated = False
        
        return res

    def unlink(self):
        for rec in self:
            if rec.next_progress:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car un avancement postérieur existe."))
            if rec.is_validated:
                raise ValidationError(_("Il n'est pas possible de supprimer cet avancement car il est validé."))
        return super().unlink()

    @api.depends('accounting_closing_id', 'accounting_closing_id.previous_closing', 'outsourcing_link_id', 
                 'progress_rate', 'accounting_closing_id.production_period_amount',
                 'rel_project_id.company_part_cost_current', 'rel_project_id.company_part_cost_futur', 
                 'rel_project_id.company_part_amount_current', 'outsourcing_product_qty')
    def compute(self):
        for rec in self:
            # 1. Type
            if rec.outsourcing_link_id:
                rec.type = rec.outsourcing_link_id.link_type
            else:
                rec.type = 'internal_production'

            # 2. Historique
            previous_closing = rec.accounting_closing_id.previous_closing
            if previous_closing:
                rec.previous_progress_id = self.env['project.progress'].search([
                    ('accounting_closing_id', '=', previous_closing.id),
                    ('outsourcing_link_id', '=', rec.outsourcing_link_id.id)
                ], limit=1)
            else:
                rec.previous_progress_id = False

            # 3. Calculs selon le type
            if rec.type == 'internal_production':
                rec.target_project_cost = (rec.rel_project_id.company_part_cost_current or 0.0) + (rec.rel_project_id.company_part_cost_futur or 0.0)
                rec.target_project_revenue = rec.rel_project_id.company_part_amount_current or 0.0
                rec.progress_cost_amount = rec.accounting_closing_id.production_period_amount or 0.0
                if rec.target_project_cost and not rec.progress_rate:
                    rec.progress_rate = rec.progress_cost_amount / rec.target_project_cost
                elif not rec.target_project_cost:
                    rec.progress_rate = 0.0

            elif rec.outsourcing_link_id:
                # Le coût total à terminaison est la somme des lignes de commmande en paiement indirect (via Tasmane) pour ce sous-traitant
                rec.target_project_cost = rec.outsourcing_link_id.order_company_payment_amount or 0.0
                # Le CA Tasmane à terminaison pour ce sous-traitant est la somme du prix de revente X ratio de paiement indirect
                #   -> En effet, dans les BCF, le prix de revente est parfois indiqué sur une seule ligne, donc on proratise
                if rec.outsourcing_link_id.order_sum_purchase_order_lines :
                    indirect_payment_ratio = rec.outsourcing_link_id.order_company_payment_amount / rec.outsourcing_link_id.order_sum_purchase_order_lines
                else:
                    indirect_payment_ratio = 1.0
                rec.target_project_revenue = (rec.outsourcing_link_id.outsource_part_amount_current or 0.0) * indirect_payment_ratio

                rec.outsourcing_product_qty_period = rec.outsourcing_product_qty - (rec.previous_progress_id.outsourcing_product_qty or 0.0)
                rec.target_project_outsourcing_product_qty = rec.outsourcing_link_id.order_sum_purchase_order_product_qty
                if rec.target_project_outsourcing_product_qty :
                    rec.progress_rate = rec.outsourcing_product_qty / rec.target_project_outsourcing_product_qty
                else :
                    rec.progress_rate = 0.0
                
                rec.progress_cost_amount = (rec.target_project_cost or 0.0) * (rec.progress_rate or 0.0)

            else:
                rec.target_project_cost = 0.0
                rec.target_project_revenue = 0.0


            rec.progress_revenue_amount = (rec.target_project_revenue or 0.0) * (rec.progress_rate or 0.0)
            
            # 5. Calcul des variations de la période (Cumulé - Précédent)
            rec.progress_revenue_amount_period = rec.progress_revenue_amount - (rec.rel_previous_progress_revenue_amount or 0.0)
            rec.progress_cost_amount_period = rec.progress_cost_amount - (rec.rel_previous_progress_cost_amount or 0.0)
            rec.progress_rate_period = rec.progress_rate - (rec.rel_previous_progress_rate or 0.0)
            
            # 6. Next Progress logic (inspired by project.accounting_closing)
            next_progress = self.env['project.progress'].search([('previous_progress_id', '=', rec.id)], limit=1)
            rec.next_progress = next_progress
            if next_progress:
                next_progress.compute()

    # --- MÉTHODES INVERSE (Cartographie vers l'entrée Maître : Taux pour Interne / Quantité pour S/T) ---
    def _inverse_progress_rate(self):
        """Si on saisit le taux, on mappe vers le champ source approprié"""
        for rec in self:
            if rec.type == 'internal_production':
                pass # Le champ lui-même est mis à jour, compute respectera la valeur (Approche B)
            elif rec.target_project_outsourcing_product_qty:
                rec.outsourcing_product_qty = rec.progress_rate * rec.target_project_outsourcing_product_qty

    def _inverse_progress_rate_period(self):
        for rec in self:
            new_rate = (rec.rel_previous_progress_rate or 0.0) + (rec.progress_rate_period or 0.0)
            if rec.type == 'internal_production':
                rec.progress_rate = new_rate
            elif rec.target_project_outsourcing_product_qty:
                rec.outsourcing_product_qty = new_rate * rec.target_project_outsourcing_product_qty

    def _inverse_qty_period(self):
        """Si on saisit la variation de la période, on met à jour le cumul (master)"""
        for rec in self:
            if rec.type != 'internal_production':
                rec.outsourcing_product_qty = (rec.previous_progress_id.outsourcing_product_qty or 0.0) + (rec.outsourcing_product_qty_period or 0.0)

    def _inverse_revenue(self):
        for rec in self:
            if rec.target_project_revenue:
                rate = rec.progress_revenue_amount / rec.target_project_revenue
                if rec.type == 'internal_production':
                    rec.progress_rate = rate
                elif rec.target_project_outsourcing_product_qty:
                    rec.outsourcing_product_qty = rate * rec.target_project_outsourcing_product_qty

    def _inverse_revenue_period(self):
        for rec in self:
            if rec.target_project_revenue:
                new_rev = (rec.rel_previous_progress_revenue_amount or 0.0) + (rec.progress_revenue_amount_period or 0.0)
                rate = new_rev / rec.target_project_revenue
                if rec.type == 'internal_production':
                    rec.progress_rate = rate
                elif rec.target_project_outsourcing_product_qty:
                    rec.outsourcing_product_qty = rate * rec.target_project_outsourcing_product_qty

    def goto_napta(self):
        self.ensure_one()
        return self.accounting_closing_id.goto_napta()

    def action_open_analytic_lines(self):
        self.ensure_one()
        return self.accounting_closing_id.action_open_analytic_lines()

    def action_validate(self):
        self.ensure_one()
        self.write({'is_validated': True})

    def action_invalidate(self):
        self.ensure_one()
        self.write({'is_validated': False})

    @api.constrains('outsourcing_link_id', 'accounting_closing_id')
    def _check_project_consistency(self):
        for rec in self:
            if rec.outsourcing_link_id and rec.accounting_closing_id:
                # On compare les IDs pour éviter les problèmes de recordset vide
                link_project_id = rec.outsourcing_link_id.project_id.id
                closing_project_id = rec.accounting_closing_id.project_id.id
                if link_project_id and closing_project_id and link_project_id != closing_project_id:
                    raise ValidationError(_("Le lien de sous-traitance (%s) doit appartenir au même projet que la clôture (%s).") % (rec.outsourcing_link_id.project_id.name, rec.accounting_closing_id.project_id.name))
