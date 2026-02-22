from odoo import models, fields, api, _

class ResPartnerIndustry(models.Model):
    _inherit = 'res.partner.industry'

    agreement_ids = fields.Many2many('agreement', compute='_compute_agreement_ids', string="Accords")
    agreement_count = fields.Integer(compute='_compute_agreement_ids', string="Nombre d'accords")

    def _compute_agreement_ids(self):
        for rec in self:
            partner_ids = rec.partner_ids.ids
            if not partner_ids:
                rec.agreement_ids = False
                rec.agreement_count = 0
                continue
            agreements = self.env['agreement'].search([
                '|',
                ('partner_id', 'in', partner_ids),
                ('partner_company_ids', 'in', partner_ids)
            ])
            rec.agreement_ids = agreements
            rec.agreement_count = len(agreements)

    def action_view_agreements(self):
        self.ensure_one()
        return {
            'name': _("Accords - %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'agreement',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.agreement_ids.ids)],
            'context': {'default_industry_id': self.id},
        }
