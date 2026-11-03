from odoo import fields, models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    lucca_id = fields.Char(string="ID Lucca", readonly=True, copy=False)
