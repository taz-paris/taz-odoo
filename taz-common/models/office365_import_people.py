# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

DOMAIN_EXCLUSION = "@tasmane.com"
    
class tazOfficePeople(models.TransientModel):
     _name = 'taz.office_people'
     _rec_name = 'display_name'
     _description = "Transient object for Office 365 contact import  (with the /people Microsoft graph API)"
     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     display_name = fields.Char(string="Office display name")
     parent_id = fields.Many2one('res.partner', string="Société", domain="[('is_company', '!=', False)]")
     odoo_contact_id = fields.Many2one('res.partner', string="Contact", domain="[('is_company', '=', False)]")
     already_in_odoo = fields.Boolean("Déjà sur Odoo")
     user_id = fields.Many2one('res.users', string="Propriétaire")
     origin_user_id = fields.Many2one('res.users', string="Utilisateur", required=True, readonly=True, help="Utilisateur Odoo du compte Office 365 qui a importé le contact - utilisé pour filtré") 
     email = fields.Char(string="email")
     category_id = fields.Many2many('res.partner.category', column1='taz_office_people_id',
                                    column2='category_id', string='Étiquettes clients')

     #def write(self, vals):
     #   res = super().write(vals)
     #   if self._context.get('change_parent_id') != False :
     #       if 'parent_id' in vals.keys():
     #           domain_target = self.email.split("@")[1]
     #           liste = self.search([('already_in_odoo', '=', False), ('origin_user_id', '=', self.env.user.id), ('email', 'like', domain_target)])
     #           for li in liste :
     #               if li.id != self.id:
     #                   _logger.info('change : '+li.email)
     #                   li.with_context(change_parent_id=False).parent_id = vals['parent_id']


     def import_partner(self):
        model = self.env['res.partner']
        #Le passage par contexte permet de récupérer les valeurs du champ qui était en cours d'éditition lorsque l'utilisatuer a cliqué sur le bouton "Créer sur Odoo"
            # ça évite de perdre la
        self.category_id = self.env.context.get('category_id')
        self.parent_id = self.env.context.get('parent_id')
        self.first_name = self.env.context.get('first_name').strip().title()
        self.last_name = self.env.context.get('last_name').strip().upper()
        self.user_id = self.env.context.get('user_id')

        count_name = model.search([('active', '=', True), ('first_name', '=ilike', self.first_name), ('name', '=ilike', self.last_name), ('is_company', '=', False), ('type', '=', 'contact')])
        if (len(count_name) >0):
            liste_match = []
            for i in count_name :
                 match = _("ID = %s, Entreprise = %s, Email=%s" % (str(i.id), i.parent_id.name or "", i.email or ""))
                 liste_match.append(match)
            raise ValidationError(_("%s autre(s) contact(s) a(ont) le même prénom (%s) et le même nom (%s). Il n'est pas possible de l'importer, mais vous pouvez le créer à la main si c'est un pur homonyme ou mettre à jour son email le cas échéant, en passant par le menu de gestion des contacts.\n\n\nListe des contacts :\n%s" % (str(len(count_name)),self.first_name, self.last_name, '\n'.join(liste_match) or "")))
        #Créer le partner Odoo
        res = {
                    'first_name' : self.first_name,
                    'name' : self.last_name,
                    'email' : self.email,
                    'parent_id' : self.parent_id.id, 
                    'is_company' : False,
                    'category_id' : self.category_id,
                    }
        if self.user_id:
            res['user_id'] = self.user_id.id
        r = model.create(res)
        _logger.info(r)
        self.odoo_contact_id = r
        self.first_name = "déjà importé"
        self.last_name = "dans la base contacts"
        self.parent_id = False
        self.user_id = False
        self.category_id = [(6,0,[])]
        #return {
        #       'type': 'ir.actions.client',
        #       'tag': 'reload',
        #    }


     def open_res_partner(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = int(self.odoo_contact_id.id)
        _logger.info(rec_id)
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref("taz-common.contact_form")

        # then open the form
        return {
                'type': 'ir.actions.act_window',
                'name': 'Contact',
                'res_model': 'res.partner',
                'res_id': rec_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': form_id.id,
                'context': {},
                # if you want to open the form in edit mode direclty
                'flags': {'initial_mode': 'edit'},
                'target': 'new',
                #'target': 'current',
            }

     @api.model
     def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        #s'il n'y a aucun enregistrement pour l'utilisateur appeler get_office365_people
        _logger.info("=========== Search read pour l'utilisateur %s %s" % (self.env.user.id, self.env.user.name))
        if self.search([('user_id', '=', self.env.user.id)], count=True) == 0 :
            #raise AccessDenied(_('Token de session Microsoft invalide : veuillez vous déconnecter puis vous reconnecter en SSO'))
            self.get_office365_people()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)
     
    #def refresh_office365_people(self): #TODO : ajouter un bouton de rafraichissement manuel
         #forcer le raffraichissement pour un utilisateur => pas sur que ça soit utile car le transienModel est vaccum toutes les heures
         #del all people for the current user
         #self.get_office365_people()

     def get_office365_people(self):
        _logger.info("=========== get_office365_people pour l'utilisateur %s %s" % (self.env.user.id, self.env.user.name))
        data = self.env.user._msgraph_people()
        _logger.info("=========== Nombre d'email retournés %s %s %s" % (str(len(data)), self.env.user.id, self.env.user.name))
        res = []

        mapping_email_id_contact = {}
        lc = self.env['res.partner'].search(['|', '|', ('email', '!=', False), ('personal_email', '!=', False), ('former_email_address', '!=', False), ('is_company', '=', False)])
        for c in lc:
            if c.email:
                mapping_email_id_contact[c.email.lower()] = c
            if c.personal_email:
                mapping_email_id_contact[c.personal_email.lower()] = c
            if c.former_email_address:
                for mail in c.former_email_address.split(','):
                    mapping_email_id_contact[mail.lower()] = c

        #_logger.info(">>>>>>>>>>>"+str(mapping_email_id_contact['dfeldman@dfcpartners.fr']))

        #TODO : ajouter une vue filtre avec par défaut le masquage des gens déjà dans Odoo
        #TODO : idée => ajouter un bouton d'exlucsion pour ne pas reproposer le contact ? => dans ce cas il ne faut pas un model Transient et il faut gérer la mise à jour en delta de ce qui vient d'Office
        for i in data :
            for mail in i["scoredEmailAddresses"]: #S'il y a plus d'une adresse pour un contact, c'est à  l'utilisateur de choisir quel contact créer sur Odoo
                if DOMAIN_EXCLUSION in mail["address"] :
                    continue

                odoo_contact_id = None
                if mail["address"].lower() in mapping_email_id_contact.keys():
                    odoo_contact_id = mapping_email_id_contact[mail["address"].lower()].id

                already_in_odoo = False
                if odoo_contact_id :
                    already_in_odoo = True

                # TODO couleur warning si nom / prénom existe déjà en base pour ne pas remettre des vieilles adresses email d'anciens postes
                computed_fname = ""
                computed_lname = ""
                parent_id = False
                user_id = False

                if not already_in_odoo :
                    l = mail["address"].split("@")[0].split('.')
                    computed_fname = l[0].title()
                    if (len(l) > 1):
                        computed_lname = '.'.join(l[1:]).upper()

                    domain_target = mail["address"].split("@")[1]
                    cl = self.env['res.partner'].search([('is_company', '=', 'True'),('child_mail_address_domain_list', 'like', domain_target)], order="write_date desc")
                    if cl:
                        parent_id = cl[0].id
                    user_id = self.env.user.id

                res.append({
                    'display_name':i['displayName'],
                    'first_name' : computed_fname,
                    'last_name' : computed_lname,
                    'email' : mail["address"],
                    'user_id' : user_id,
                    'origin_user_id': self.env.user.id,
                    'parent_id' : parent_id, 
                    'odoo_contact_id' : odoo_contact_id,
                    'already_in_odoo' : already_in_odoo,
                    })
        self.create(res)

