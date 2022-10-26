# -*- coding: utf-8 -*-

from odoo import models, fields, api


class tazResPartner(models.Model):
     _inherit = "res.partner"
     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     parent_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='parent_id.industry_id')  #store=True

     business_action_ids = fields.One2many('taz.business_action', 'partner_id') 


     @api.onchange('first_name', 'last_name')
     def _compute_fields_combination(self):
         for test in self:
             if not test.first_name and not test.last_name:
                test.name = ""
             elif test.first_name and not test.last_name:
                 test.name = test.first_name
             elif test.last_name and not test.first_name :
                 test.name = test.last_name
             else :
                test.name = test.first_name + ' ' + test.last_name
#     _description = 'taz-common.taz-common'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
