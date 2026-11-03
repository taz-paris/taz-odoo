from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    lucca_id = fields.Char(string="ID Lucca", readonly=True, copy=False)
