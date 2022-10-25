# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class taz-common(models.Model):
#     _name = 'taz-common.taz-common'
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
