# -*- coding: utf-8 -*-

from odoo import models, fields, api


class tazResPartner(models.Model):
     _inherit = "res.partner"
     

     def _compute_child_mail_address_domain_list(self):
         domain_list = []
         for child in self.child_ids:
             if child.email:
                 domain = child.email.split("@")[1]
                 if ',' in domain :
                     continue
                 if domain and domain not in domain_list:
                     domain_list.append(domain)
         self.child_mail_address_domain_list = ','.join(domain_list)

     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     parent_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='parent_id.industry_id')  #store=True

     business_action_ids = fields.One2many('taz.business_action', 'partner_id') 
     child_mail_address_domain_list = fields.Char('Liste domaines mail', compute=_compute_child_mail_address_domain_list) #store=True

     @api.onchange('first_name', 'last_name')
     def _compute_fields_combination(test):
     #def write(self, vals):
     #    super().write(vals)
         if not test.first_name and not test.last_name:
            test.name = ""
         elif test.first_name and not test.last_name:
             test.name = test.first_name
         elif test.last_name and not test.first_name :
             test.name = test.last_name
         else :
            test.name = test.first_name + ' ' + test.last_name
