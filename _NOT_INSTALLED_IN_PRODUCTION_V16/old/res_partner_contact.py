# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _


class tazResPartner(models.Model):
     _inherit = "res.partner"
     

     @api.depends('child_ids')
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
     parent_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='parent_id.industry_id', store=True)

     business_action_ids = fields.One2many('taz.business_action', 'partner_id') 
     child_mail_address_domain_list = fields.Char('Liste domaines mail', compute=_compute_child_mail_address_domain_list, store=True)


     def name_get(self):
         res = []
         for rec in self:
             if (rec.is_company == False):
                 res.append((rec.id, "%s %s (%s)" % (rec.first_name, rec.name or "", rec.parent_id.name or "")))
             else:
                 res.append((rec.id, "%s" % rec.name))
         return res

     @api.constrains('email')
     def _check_email(self):
         count_email = self.search_count([('email', '=', self.email), ('is_company', '=', False)])
         if count_email > 1 and self.email is not False:
             raise ValidationError(_('Cette adresse email est déjà utilisée sur une autre fiche contact. Enregistrement impossible (il ne faudrait pas créer des doublons de contact ;-)) !'))

