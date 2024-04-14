from odoo import _, api, fields, models

    
class Agreement(models.Model):
    _inherit = "agreement"

    project_ids = fields.One2many('project.project', 'agreement_id') 
