# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import re

from odoo.addons import base
#base.models.res_partner.ADDRESS_FIELDS += ('street3',)

class tazResPartner(models.Model):
     _inherit = "res.partner"
     
     def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(street3)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

     def write(self, vals):
        # il est nécessaire de forcer le recacul des noms de domaine de l'ancien parent_id
        old_parent_id = None
        if 'parent_id' in vals.keys():
            old_parent_id = self.parent_id

        old_personal_email = self.personal_email
        if old_personal_email:
            old_personal_email = old_personal_email.strip().lower()
        old_email = self.email
        if old_email:
            old_email = old_email.strip().lower()

        res = super().write(vals)

        if old_parent_id: 
            old_parent_id._compute_child_mail_address_domain_list()

        if self._context.get('save_forme_address') != False :
            former = []
            if self.former_email_address:
                former = self.former_email_address.split(',')
                if self.personal_email in former:
                    former.remove(self.personal_email)
                if self.email in former:
                    former.remove(self.email)
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
            else : 
                self.with_context(save_forme_address=False).former_email_address = False

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

     street3 = fields.Char('Rue3')
     title = fields.Many2one(string="Civilité")

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

     @api.model
     def fields_get(self, allfields=None, attributes=None):
        hide = ['message_is_follower', 'message_follower_ids', 'message_partner_ids', 'message_ids', 'has_message', 'message_needaction', 'message_needaction_counter', 'message_has_error', 'message_has_error_counter', 'message_attachment_count', 'message_main_attachment_id', 'website_message_ids', 'email_normalized', 'is_blacklisted', 'message_bounce', 'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id', 'activity_type_icon', 'activity_date_deadline', 'my_activity_date_deadline', 'activity_summary', 'activity_exception_decoration', 'activity_exception_icon', 'activity_calendar_event_id', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'avatar_1920', 'avatar_1024', 'avatar_512', 'avatar_256', 'avatar_128', 'name', 'display_name', 'date', 'lang', 'active_lang_count', 'tz', 'tz_offset', 'user_id', 'vat', 'same_vat_partner_id', 'same_company_registry_partner_id', 'company_registry', 'bank_ids', 'employee', 'partner_latitude', 'partner_longitude','email_formatted', 'is_public', 'company_type', 'company_id', 'color', 'user_ids', 'partner_share', 'contact_address', 'commercial_partner_id', 'commercial_company_name', 'company_name', 'barcode','im_status', 'channel_ids', 'signup_token', 'signup_type', 'signup_expiration', 'signup_valid', 'signup_url', 'meeting_count', 'meeting_ids', 'calendar_last_notif_ack', 'employee_ids', 'employees_count', 'property_product_pricelist', 'team_id', 'certifications_count', 'certifications_company_count', 'event_count', 'payment_token_ids', 'payment_token_count', 'child_ids_company', 'child_ids_contact', 'credit', 'credit_limit', 'use_partner_credit_limit', 'show_credit_limit', 'debit', 'debit_limit', 'total_invoiced', 'currency_id', 'journal_item_count', 'property_account_payable_id', 'property_account_receivable_id', 'property_account_position_id', 'property_payment_term_id', 'property_supplier_payment_term_id', 'ref_company_ids', 'has_unreconciled_entries', 'last_time_entries_checked', 'invoice_ids', 'contract_ids', 'bank_account_count', 'trust', 'invoice_warn', 'invoice_warn_msg', 'supplier_rank', 'customer_rank', 'duplicated_bank_account_partners_count', 'opportunity_ids', 'opportunity_count', 'task_ids', 'task_count', 'property_purchase_currency_id', 'purchase_order_count', 'supplier_invoice_count', 'purchase_warn', 'purchase_warn_msg', 'receipt_reminder_email', 'reminder_date_before_receipt', 'siret']
        #par déduction, champs restant au 03/12/2022 : 'mailchimp_status’, 'is_priority_target', 'former_email_address', 'assistant', 'date_last_business_action', 'street3', 'personal_phone', 'personal_email', 'linkedin_url', 'business_action_ids', 'child_mail_address_domain_list', 'customer_book_goal_ids', 'customer_book_followup_ids, 'first_name', 'long_company_name', 'parent_industry_id', 'id', '__last_update', 'create_uid', 'create_date', 'write_uid', 'write_date', 'email','phone', 'mobile', 'is_company', 'is_public', 'industry_id', 'function', 'type', 'street', 'street2', 'zip', 'city', 'state_id', 'country_id', 'country_code’, 'website', 'comment', 'category_id', 'active',  'title', 'parent_id', 'parent_name', 'child_ids', 'ref', 
        #_logger.info(res.keys())
        res = super().fields_get()
        for field in hide:
            #res[field]['sortable'] = False // To Hide Field From Group by
            #res[field]['exportable'] = False // To Hide Field From Export List
            res[field]['searchable'] = False
        return res

     @api.constrains('email', 'personal_email', 'active')
     def _check_email(self):
         for mail in [self.email, self.personal_email]:
             if mail:
                 regex = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")
                 if not(re.fullmatch(regex, mail)):
                     raise ValidationError(_('Cette adresse email est invalide : %s' % mail))

             email_list = self.search(['|', '|', ('email', '=ilike', mail), ('personal_email', '=ilike', mail), ('former_email_address', 'ilike', mail), ('is_company', '=', False), ('type', '=', 'contact'), ('active', '=', True)])
             list_match = []
             for e in email_list :
                 if str(e.id) != str(self.id).replace("New_", ""):
                    list_match.append("%s [id = %s]" % (e.name_get()[0][1], str(e.id)))
             if len(email_list) > 1 and mail is not False:
                 raise ValidationError(_('Cette adresse email est déjà utilisée sur une autre fiche contact (dans le champ email ou email personnel ou anciennes adresses email). Enregistrement impossible (il ne faudrait pas créer des doublons de contact ;-)) ! \n\nContact concerné : %s' % ('\n'.join(list_match) or "")))

     @api.constrains('first_name')
     def _check_firstname(self):
         if (self.is_company == False and self.type=='contact'):
             if not(self.first_name):
                raise ValidationError(_('Vous devez indiquer un prénom et un nom.'))

     @api.constrains('name')
     def _check_name(self):
         if (self.is_company == True and self.type=='contact'):
             count_name = self.search_count([('name', '=ilike', self.name), ('is_company', '=', True), ('type', '=', 'contact'), ('active', '=', True)])
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
                     lc = self.env['res.partner'].search([('child_mail_address_domain_list', 'ilike', domain), ('is_company', '=', True), ('active', '=', True)], order="write_date desc")
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
         lc = self.env['res.partner'].search([('child_mail_address_domain_list', 'ilike', domain), ('is_company', '=', True), ('active', '=', True)], order="write_date desc")
         if len(lc) > 0:
             coherent = False
             list_match = []
             for c in lc:
                list_match.append("%s [ID=%s]" % (c.name, str(c.id)))
                if str(self.parent_id.id).replace('NewId_','') == str(c.id): #quand on passe par l'entreprise, et que l'on ouvre la popup de modification d'un contact lié, l'id parent est en mémoire, et il est préfixé par "NewID"
                    coherent = True
             if coherent == False :
                 return {
                    'warning': {
                        'title': _("Attention : est-ce la bonne entreprise ?"),
                        'message': _("Le domaine de l'adresse email est présent dans les contacts de %s autre(s) entreprise(s)... mais pas celle sélectionnée. N'y aurait-il pas un soucis ?  \n\n\nListe des entreprises dont au moins un contact a une adresse email avec ce nom de domaine(%s) : \n%s" % (len(list_match), domain, '\n'.join(list_match) or ""))
                        }
                 }
         return False


     @api.onchange('first_name', 'name')
     def _onchange_name(self):
         if (self.first_name and self.name):
             if (self.is_company == False and self.type=='contact'):
                 if self._origin.id:
                    count_name = self.search([('id', '!=', self._origin.id), ('active', '=', True), ('first_name', '=ilike', self.first_name), ('name', '=ilike', self.name), ('is_company', '=', False), ('type', '=', 'contact')])
                 else:
                    count_name = self.search([('active', '=', True), ('first_name', '=ilike', self.first_name), ('name', '=ilike', self.name), ('is_company', '=', False), ('type', '=', 'contact')])
                 if (len(count_name) >0):
                    liste_match = []
                    for i in count_name :
                         match = _("ID = %s, Entreprise = %s" % (str(i.id), i.parent_id.name or ""))
                         liste_match.append(match)
                    return {
                        'warning': {
                            'title': _("Attention : possibilité de doublons !"),
                            'message': _("%s autre(s) contact(s) a(ont) le même nom et le même prénom, vérifiez bien que vous n'êtes pas en train de créer un contact en doublon ! \n    => S'il s'agit d'un réel homonyme, vous pouvez continuer. \n    => S'il s'agit d'un doublon, merci de cliquer sur le bouton d'annulation (en haut de l'écran, à droit de 'Nouveau') \n\n\nListe des contacts :\n%s" % (str(len(count_name)), '\n'.join(liste_match) or ""))
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

     @api.onchange('street3')
     def onchange_street3(self):
         if self.street3 :
            self.street3 = self.street3.strip().upper()

     @api.onchange('city')
     def onchange_city(self):
         if self.city :
            self.city = self.city.strip().upper()
     
     def filter_name_duplicate(self):
        _logger.info('=========== filter_name_duplicate')
        contacts = self.search([('is_company', '=', False), ('active','=',True), ('type', '=', 'contact'), ('user_ids', '=', False)])
        count = {}
        for c in contacts:
            nom = c.first_name.strip().title() + ' ' + c.name.strip().upper()
            if nom not in count.keys():
                count[nom] = []
            count[nom].append(c)
        res = []
        for nom, partner_ids in count.items():
            if len(partner_ids) > 1:
                for p in partner_ids:
                    if p.id not in res :
                        res.append(p.id)
                _logger.info('     => %s est présent %s fois' % (nom, str(len(partner_ids))))
        domain = [('id', 'in', res)]

        return {
                'type': 'ir.actions.act_window',
                'name': 'Contacts - homonymes nom/prénom ou doublons',
                'res_model': 'res.partner',
                'view_type': 'tree',
                'view_mode': 'tree,form',
                'view_id': [self.env.ref("taz-common.contact_tree").id, self.env.ref("taz-common.contact_form").id],
                'context': {},
                'domain':domain,
                # if you want to open the form in edit mode direclty
                'target': 'current',
            }
 
     def filter_company_shared_email_domain(self):
         _logger.info('=========== filter_company_shared_email_domain')
         companies = self.search([('is_company', '=', True), ('active','=',True), ('user_ids', '=', False)])
         #for c in companies:
         #    c._compute_child_mail_address_domain_list()
         count = {}
         for c in companies:
             if c.child_mail_address_domain_list:
                 list_domain = c.child_mail_address_domain_list.split(',')
                 for domain in list_domain:
                     if domain not in count.keys():
                         count[domain] = []
                     count[domain].append(c)
         res = []
         for domain, partner_ids in count.items():
             if len(partner_ids) > 1:
                for p in partner_ids:
                    if p.id not in res :
                        res.append(p.id)
         domain = [('id', 'in', res)]
         return {
                'type': 'ir.actions.act_window',
                'name': 'Entreprises qui partagent au moins un nom de domaine email avec une autre entreprise (non archivée)',
                'res_model': 'res.partner',
                'view_type': 'tree',
                'view_mode': 'tree,form',
                'view_id': [self.env.ref("taz-common.company_tree").id, self.env.ref("taz-common.company_form").id],
                'context': {},
                'domain':domain,
                # if you want to open the form in edit mode direclty
                'target': 'current',
            }

     @api.model
     def normalize_partner_casse(self):
        if self.first_name :
            self.first_name = self.first_name.strip().title()
        if self.name :
            self.name = self.name.strip().upper()
        if self.email :
            self.email = self.email.strip().lower()
        if self.personal_email :
            self.personal_email = self.personal_email.strip().lower()
        if self.street :
            self.street = self.street.strip().upper()
        if self.street2 :
            self.street2 = self.street2.strip().upper()
        if self.street3 :
            self.street3 = self.street3.strip().upper()
        if self.city :
            self.city = self.city.strip().upper()

     @api.onchange('parent_id')
     def onchange_parent_id(self): #REMPLACE LA FONCTION NATIVE ODOO POUR NE PLUS CONSEILLER DE CREER UNE NOUVELLE FICHE CONTACT SI LE CONTACT CHANGE D'ENTREPRISE
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

#Wizzard de fusion / déduplication :
    #https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/odoo/addons/base/wizard/base_partner_merge.py
    #https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/odoo/addons/base/wizard/base_partner_merge_views.xml
