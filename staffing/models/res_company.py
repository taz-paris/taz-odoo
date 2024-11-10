from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_hr_department_for_projects_id = fields.Many2one('hr.department', string="Département par défaut pour les projets")
