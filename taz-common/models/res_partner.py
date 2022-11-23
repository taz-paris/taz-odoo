# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import re

class tazResPartner(models.Model):
     _inherit = "res.partner"
     
     def write(self, vals):
        # il est nécessaire de forcer le recacul des noms de domaine de l'ancien parent_id
        old_parent_id = None
        if 'parent_id' in vals.keys():
            old_parent_id = self.parent_id

        old_personal_email = self.personal_email
        old_email = self.email

        res = super().write(vals)

        if old_parent_id: 
            old_parent_id._compute_child_mail_address_domain_list()

        if self._context.get('save_forme_address') != False :
            former = []
            if self.former_email_address:
                former = self.former_email_address.split(',')
            if old_email :
                if old_email != self.email and old_email != self.personal_email:
                    if old_email not in former :
                        former.append(old_email)
            if old_personal_email :
                if old_personal_email != self.email and old_personal_email != self.personal_email:
                    if old_personal_email not in former :
                        former.append(old_personal_email)
            if len(former) > 0:
                self.with_context(save_forme_address=False).former_email_address = ','.join(former)

        return res

     def unlink(self):
        # il est nécessaire de forcer le recacul des noms de domaine de l'ancien parent_id
        old_parent_id = None
        if self.parent_id:
            old_parent_id = self.parent_id
        res = super().unlink()
        if old_parent_id: 
            old_parent_id._compute_child_mail_address_domain_list()
        return res

     @api.depends('child_ids','child_ids.email')
     def _compute_child_mail_address_domain_list(self):
         _logger.info("DEBUT _compute_child_mail_address_domain_list")# %s %s" % (self.name, self.child_mail_address_domain_list))
         domain_list = []
         for child in self.child_ids:
             if child.email:
                 domain = child.email.split("@")[1]
                 if ',' in domain :
                     continue
                 if domain and domain not in domain_list:
                     domain_list.append(domain)
         self.child_mail_address_domain_list = ','.join(domain_list)
         _logger.info("FIN _compute_child_mail_address_domain_list")

     @api.depends('business_action_ids')
     def _compute_date_last_business_action(self):
         res = None
         for action in self.business_action_ids:
             if action.state == 'done' :
                 if res == None or action.date_deadline < res:
                     res = action.date_deadline
         self.date_last_business_action = res


     first_name = fields.Char(string="Prénom")
     long_company_name = fields.Char(string="Libellé long de société")
     parent_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='parent_id.industry_id', store=True)
     child_ids_company = fields.One2many('res.partner', 'parent_id', string='Entreprises du groupe', domain=[('active', '=', True), ('is_company', '=', True)]) 
     child_ids_contact = fields.One2many('res.partner', 'parent_id', string='Contacts rattchés à cette entreprise', domain=[('active', '=', True), ('is_company', '=', False)]) 
     is_priority_target = fields.Boolean("Compte à ouvrir")
     former_email_address = fields.Char("Anciennes adresses email", readonly=True)

     assistant = fields.Html('Assistant(e)')
     user_id = fields.Many2one(string="Propriétaire") #override the string of the native field
     date_last_business_action = fields.Date('Date du dernier RDV', compute=_compute_date_last_business_action, store=True)

     personal_phone = fields.Char("Tel personnel", unaccent=False)
     personal_email = fields.Char("Email personnel")
     linkedin_url = fields.Char("LinkedIn")

     business_action_ids = fields.One2many('taz.business_action', 'partner_id') 
     child_mail_address_domain_list = fields.Char('Liste domaines mail', compute=_compute_child_mail_address_domain_list, store=True)

     customer_book_goal_ids = fields.One2many('taz.customer_book_goal', 'partner_id')  
     customer_book_followup_ids = fields.One2many('taz.customer_book_followup', 'partner_id')  

     mailchimp_status = fields.Selection([('cleaned', 'cleaned'), ('nonsubscribed', 'nonsubscribed'), ('subscribed', 'subscribed'), ('unsubscribed', 'unsubscribed')], "Statut Mailchimp lors de l'import")

     def name_get(self):
         res = []
         for rec in self:
             display_name = ""
             if (rec.is_company == False):
                 display_name += "%s %s (%s)" % (rec.first_name or "", rec.name or "", rec.parent_id.name or "")
             else:
                 display_name += rec.name
                 if (rec.long_company_name):
                     display_name += " - %s" % rec.long_company_name or ""
                 if (rec.parent_id):
                     display_name += " (%s)" % rec.parent_id.name or ""
             res.append((rec.id, display_name))
         return res

     @api.model
     def name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
         args = args or []
         recs = self.browse()
         if not recs:
             recs = self.search(['|', '|', ('first_name', operator, name), ('long_company_name', operator, name), ('name', operator, name)] + args, limit=limit)
         return recs.name_get()

     #     args = args or []
     #     args = ['|', '|', ('first_name', operator, name), ('long_company_name', operator, name), ('name', operator, name)] + args
     #     return self._search(args, limit=limit, access_rights_uid=name_get_uid)
     
     #@api.model
     #def fields_get(self, allfields=None, attributes=None):
     #   res = super().fields_get(allfields, attributes=attributes)
     # ## SI l'utilisateur n'est pas un administrateur alors :
     #   fields_to_ignore_in_search = ['has_message']
     #   for field in fields_to_ignore_in_search:
     #       if res.get(field):
     #          res.get(field)['searchable'] = False
     #   return res

     @api.constrains('email', 'personal_email')
     def _check_email(self):
         for mail in [self.email, self.personal_email]:
             if mail:
                 regex = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")
                 if not(re.fullmatch(regex, mail)):
                     raise ValidationError(_('Cette adresse email est invalide : %s' % mail))

             count_email = self.search_count(['|', ('email', '=', mail), ('personal_email', '=', mail), ('is_company', '=', False), ('type', '=', 'contact')])
             if count_email > 1 and mail is not False:
                 raise ValidationError(_('Cette adresse email est déjà utilisée sur une autre fiche contact (dans le champ email ou email personnel). Enregistrement impossible (il ne faudrait pas créer des doublons de contact ;-)) !'))


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
                 raise ValidationError(_('%s : ce nom est déjà utilisé sur une autre fiche entreprise. Enregistrement impossible (il ne faudrait pas créer des doublons d\'entreprises ;-)) !' % self.name))

     @api.onchange('personal_email')
     def _onchange_personal_email(self):
         if (self.personal_email):
             self.personal_email = self.personal_email.strip().lower()

     @api.onchange('email')
     def _onchange_email(self):
         _logger.info('TRIGGER onchange_email_parent_id')
         if (self.email):
             self.email = self.email.strip().lower()
         if (self.is_company == False and self.type=='contact'):
             _logger.info(self._origin.parent_id)
             _logger.info(self.parent_id)
             if self.email and "@" in self.email :
                 l = self.email.split("@")[0].split('.')
                 #pré-remplissage du nom/prénom s'ils ne sont pas déjà remplis
                 if not(self.first_name):
                    self.first_name = l[0].title()
                 if (len(l) > 1):
                    if not(self.name) :
                        self.name = '.'.join(l[1:]).upper()

                 if self.parent_id:
                     #vérification de la cohérence entre le mail et l'entreprise
                     consistency = self._test_parent_id_email_consistency()
                     if consistency:
                        return consistency
                 else :
                     #pré-remplissage de l'entreprise
                     domain = self.email.split("@")[1] 
                     lc = self.env['res.partner'].search([('child_mail_address_domain_list', 'ilike', domain), ('is_company', '=', True)], order="write_date desc")
                     if len(lc) > 0:
                        self.parent_id = lc[0].id #on pré-rempli avec l'entreprise qui a le nom de domaine et qui a été mise à jour en dernier
                     

     @api.onchange('parent_id')
     def _onchange_parent_id(self):
         if (self.is_company == False and self.type=='contact'):
             if self.parent_id and self.email and "@" in self.email:
                 consistency = self._test_parent_id_email_consistency()
                 if consistency:
                    return consistency
                
     def _test_parent_id_email_consistency(self):
         _logger.info("_test_parent_id_email_consistency")
         domain = self.email.split("@")[1] 
         lc = self.env['res.partner'].search([('child_mail_address_domain_list', 'ilike', domain), ('is_company', '=', True)], order="write_date desc")
         coherent = False
         list_match = []
         if len(lc) > 0:
             for c in lc:
                list_match.append(c.name)
                if str(self.parent_id.id).replace('NewId_','') == str(c.id): #quand on passer par l'entreprise, et que l'on ouvre la popup de modification d'un contact lié, l'id parent est en mémoire, et il est préfixé par "NewID"
                    coherent = True
         if coherent == False :
             return {
                'warning': {
                    'title': _("Attention : est-ce la bonne entreprise ?"),
                    'message': _("Le domaine de l'adresse email est présent dans les contacts d'au moins une autre entreprise... mais pas celle sélectionnée. N'y aurait-il pas un soucis ?  \n\n\nListe des entreprises dont au moins un contact a une adresse email avec ce nom de domaine(%s) : \n%s" % (domain, '\n'.join(list_match) or ""))
                    }
             }

    #def refresh_all_company_mail_address_domain_list(self):
         #p = self.search([('is_company', '=', True)])
         #for par in p:
         #    par._compute_child_mail_address_domain_list()

     @api.onchange('first_name', 'name')
     def _onchange_name(self):
         if (self.first_name and self.name):
             if (self.is_company == False and self.type=='contact'):
                 count_name = self.search([('first_name', '=ilike', self.first_name), ('name', '=ilike', self.name), ('is_company', '=', False), ('type', '=', 'contact')])
                 if len(count_name) > 0:
                    liste_match = []
                    for i in count_name :
                         match = _("ID = %s, Entreprise = %s" % (str(i.id), i.parent_id.name or ""))
                         liste_match.append(match)
                    return {
                        'warning': {
                            'title': _("Attention : possibilité de doublons !"),
                            'message': _("%s autre(s) contact(s) a(ont) le même nom et le même prénom, vérifiez bien que vous n'êtes pas en train de créer un contact en doublon ! \n    => S'il s'agit d'un réel homonyme, vous pouvez continuer. \n    => S'il s'agit d'un doublon, merci de cliquer sur le bouton d'annulation (en haut de l'écran, à droit de 'Nouveau') \n\n\nListe des contacts :\n%s" % (str(count_name), '\n'.join(liste_match) or ""))
                                  }
                    }
                 self.first_name = self.first_name.strip().title()
                 self.name = self.name.strip().upper()
                 _logger.info('onchange first_name, name')


     @api.onchange('street')
     def onchange_street(self):
         if self.street :
            self.street = self.street.strip().upper()

     @api.onchange('street2')
     def onchange_street2(self):
         if self.street2 :
            self.street2 = self.street2.strip().upper()

     @api.onchange('city')
     def onchange_city(self):
         if self.city :
            self.city = self.city.strip().upper()

     @api.onchange('parent_id')
     def onchange_parent_id(self): #REMPLACE LA FONCTION DE BASE POUR NE PLUS CONSEILLER DE CREER UNE NOUVELLE FICHE CONTACT SI LE CONTACT CHANGE D'ENTREPRISE
        _logger.info('TRIGGER onchange_parent_id')
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return
        result = {}
        partner = self._origin
        #if partner.parent_id and partner.parent_id != self.parent_id:
        #    result['warning'] = {
        #        'title': _('Warning'),
        #        'message': _('Changing the company of a contact should only be done if it '
        #                     'was never correctly set. If an existing contact starts working for a new '
        #                     'company then a new contact should be created under that new '
        #                     'company. You can use the "Discard" button to abandon this change.')}
        if partner.type == 'contact' or self.type == 'contact':
            # for contacts: copy the parent address, if set (aka, at least one
            # value is set in the address: otherwise, keep the one from the
            # contact)
            address_fields = self._address_fields()
            if any(self.parent_id[key] for key in address_fields):
                def convert(value):
                    return value.id if isinstance(value, models.BaseModel) else value
                result['value'] = {key: convert(self.parent_id[key]) for key in address_fields}
        _logger.info('FIN TRIGGER onchange_parent_id')
        return result

     #@api.model
     #def create(self, vals):
     #   if not vals.get("parent_id"):
     #       vals["parent_id"] = self._context.get("default_parent_id")
     #   return super().create(vals)



#Wizzard de fusion / déduplication :
    #https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/odoo/addons/base/wizard/base_partner_merge.py
    #https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/odoo/addons/base/wizard/base_partner_merge_views.xml
