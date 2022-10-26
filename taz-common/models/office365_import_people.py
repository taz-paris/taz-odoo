# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

DOMAIN_EXCLUSION = "@tasmane.com"
MSGRAPH_PAGE_SIZE = 500
    
class tazOfficePeople(models.TransientModel):
     _name = 'taz.office_people'
     _rec_name = 'display_name'
     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     display_name = fields.Char(string="Office display name")
     parent_id = fields.Many2one('res.partner', string="Société") #, domain="[('is_company', '=', False)]"
     odoo_id = fields.Char(string="Contact") #, domain="[('is_company', '=', False)]"
     user_id = fields.Many2one('res.users', string="Utilisateur", required=True) #, domain="[('is_company', '=', False)]"
     email = fields.Char(string="email")
     #user_id vendeur 

     def import_partner(self):
        model = self.env['res.partner']
        res = {
                    'first_name' : self.first_name,
                    'last_name' : self.last_name,
                    'name' : self.first_name + ' ' + self.last_name,
                    'email' : self.email,
                    'user_id' : self.env.user.id,
                    'parent_id' : self.parent_id.id, 
                    'is_company' : False,
                    }
        r = model.create(res)
        _logger.info(r)
        self.odoo_id = r.id


     def open_res_partner(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = int(self.odoo_id)
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
                'target': 'current',
            }

     @api.model
     def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        #s'il n'y a aucun enregistrement pour l'utilisateur appeler get_office365_people
        if self.search([('user_id', '=', self.env.user.id)], count=True) == 0 :
            self.get_office365_people()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)
     
    #def refresh_office365_people(self): #TODO : ajouter un bouton de rafraichissement manuel
         #forcer le raffraichissement pour un utilisateur => pas sur que ça soit utile car le transienModel est vaccum toutes les heures
         #del all people for the current user
         #self.get_office365_people()

     def get_office365_people(self):
        data = self.env.user._msgraph_people()
        res = []

        for i in data :
            for mail in i["scoredEmailAddresses"]: #S'il y a plus d'une adresse pour un contact, c'est à  l'utilisateur de choisir quel contact créer sur Odoo
                if DOMAIN_EXCLUSION in mail["address"] :
                    continue
                #if mail["address"].lower() in mailchimpMembersMails : #TODO ne retourner que les contacts Outlook qui ne sont pas encore dans Odoo
                #    continue
                # TODO couleur warning si nom / prénom existe déjà en base pour ne pas remettre des vieilles adresses email d'anciens postes
                computed_fname = ""
                computed_lname = ""
                l = mail["address"].split("@")[0].split('.')
                computed_fname = l[0].title()
                if (len(l) > 1):
                    computed_lname = '.'.join(l[1:]).upper()

                domain_target = mail["address"].split("@")[1]
                #m = self.pool.get('res.partner')
                cl = self.env['res.partner'].search([('is_company', '=', 'True'),('child_mail_address_domain_list', 'like', domain_target)], order="__last_update desc")
                if cl:
                    partner_id = cl[0].id
                else:
                    partner_id = None

                res.append({
                    'display_name':i['displayName'],
                    'first_name' : computed_fname,
                    'last_name' : computed_lname,
                    'email' : mail["address"],
                    'user_id' : self.env.user.id,
                    'parent_id' : partner_id, 
                    })
        self.create(res)

       
 
class tazResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _msgraph_people(self):
        tk = self.oauth_access_token
        if not self.oauth_provider_id or not tk or 'microsoft' not in self.oauth_provider_id.data_endpoint:
            return []
        #TODO : forcer le rafraichissment du token

        contacts = []
        offset = 0
        while (True) :
            # DOCUMENTATION : https://docs.microsoft.com/fr-fr/graph/people-example
            endpoint = self.oauth_provider_id.data_endpoint + '/people?$top='+str(MSGRAPH_PAGE_SIZE)+'&select=displayName,scoredEmailAddresses&skip='+str(offset)
            graphdata = self._auth_oauth_rpc(endpoint, tk)
            #headers = {'SdkVersion': 'sample-python-flask',
            #           'x-client-SKU': 'sample-python-flask',
            #           'client-request-id': str(uuid.uuid4()),
            #           'return-client-request-id': 'true'}
            #graphdata = MSGRAPH.get(endpoint, headers=headers).data
            contacts.extend(graphdata["value"])
            if (len(graphdata["value"]) < MSGRAPH_PAGE_SIZE):
                break
            offset = offset + MSGRAPH_PAGE_SIZE
        return contacts
