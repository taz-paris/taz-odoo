from odoo import models, fields


class HrSkill(models.Model):
    _inherit = 'hr.skill'
    description = fields.Text("Description")
    is_certification = fields.Boolean("Certification")
    validity_duration_in_months = fields.Integer("Durée de validité (mois)")
