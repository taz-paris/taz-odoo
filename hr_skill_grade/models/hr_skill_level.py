from odoo import models, fields


class HrSkillLevel(models.Model):
    _inherit = 'hr.skill.level'
    description = fields.Text("Description")
