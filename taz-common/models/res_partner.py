# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

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
                 res.append((rec.id, "%s %s (%s)" % (rec.first_name or "", rec.name or "", rec.parent_id.name or "")))
             else:
                 res.append((rec.id, "%s" % rec.name))
         return res

     @api.constrains('email')
     def _check_email(self):
         count_email = self.search_count([('email', '=', self.email), ('is_company', '=', False), ('type', '=', 'contact')])
         if count_email > 1 and self.email is not False:
             raise ValidationError(_('Cette adresse email est déjà utilisée sur une autre fiche contact. Enregistrement impossible (il ne faudrait pas créer des doublons de contact ;-)) !'))

     @api.constrains('first_name')
     def _check_firstname(self):
         if (self.is_company == False and self.type=='contact'):
             if not(self.first_name):
                raise ValidationError(_('Vous devez indiquer un prénom et un nom.'))

     @api.constrains('name')
     def _check_name(self):
         if (self.is_company == True and self.type=='contact'):
             count_name = self.search_count([('name', '=ilike', self.name), ('is_company', '=', True), ('type', '=', 'contact')])
             if count_name > 1 and self.name is not False:
                raise ValidationError(_('Cette nom est déjà utilisé sur une autre fiche entreprise. Enregistrement impossible (il ne faudrait pas créer des doublons d\'entreprises ;-)) !'))

     @api.onchange('first_name', 'name')
     def _onchange_name(self):
         _logger.info("A")
         if (self.first_name and self.name):
             _logger.info("B")
             if (self.is_company == False and self.type=='contact'):
                 _logger.info("C")
                 count_name = self.search_count([('first_name', '=ilike', self.first_name), ('name', '=ilike', self.name), ('is_company', '=', False), ('type', '=', 'contact')])
                 _logger.info(count_name)
                 if count_name > 0:
                     _logger.info("E")
                     return {
                        'warning': {
                            'title': _("Attention : possibilité de doublons !"),
                            'message': _("%s autre(s) contact(s) a(ont) le même nom et le même prénom, vérifiez bien que vous n'êtes pas en train de créer un contact en doublon ! \n    => S'il s'agit d'un réel homonyme, vous pouvez continuer. \n    => S'il s'agit d'un doublon, merci de cliquer sur le bouton d'annulation (en haut de l'écran, à droit de 'Nouveau')." % (str(count_name)))
                                  }
                    }

     #@api.model
     #def create(self, vals):
     #   if not vals.get("parent_id"):
     #       vals["parent_id"] = self._context.get("default_parent_id")
     #   return super().create(vals)




class tazResUsers(models.Model):
     _inherit = "res.users"

     def name_get(self):
         res = []
         for rec in self:
            res.append((rec.id, "%s %s" % (rec.first_name or "", rec.name or "")))
         return res

