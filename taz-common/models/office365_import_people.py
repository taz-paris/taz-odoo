# -*- coding: utf-8 -*-

from odoo import models, fields, api

DOMAIN_EXCLUSION = "@tasmane.com"
MSGRAPH_PAGE_SIZE = 500
    
class tazOfficePeople(models.TransientModel):
     _name = 'taz.office_people'
     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     display_name = fields.Char(string="Office display name")
     parent_id = fields.Many2one('res.partner', string="Contact", required=True) #, domain="[('is_company', '=', False)]"
     email = fields.Char(string="email")
     #user_id vendeur 

     @api.model
     def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        #TODO lever une erreur si domain, fields, offset, limite order sont transmis
        data = self.env.user._msgraph_people()
        res = []
        id_seq = 1

        for i in data :
            for mail in i["scoredEmailAddresses"]: #S'il y a plus d'une adresse pour un contact, c'est à  l'utilisateur de choisir quel contact créer sur Odoo
                if DOMAIN_EXCLUSION in mail["address"] :
                    continue
                #if mail["address"].lower() in mailchimpMembersMails : #ne retourner que les contacts Outlook qui ne sont pas encore dans Odoo
                #    continue

                computed_fname = ""
                computed_lname = ""
                l = mail["address"].split("@")[0].split('.')
                computed_fname = l[0].title()
                if (len(l) > 1):
                    computed_lname = '.'.join(l[1:]).upper()

                #societe =  getMappingDomaineSocietes(mail["address"])
                #societe = ""
                #if societe == "":
                #    domain_target = mail["address"].split("@")[1]
                #    d = domain_target.split(".")
                #    d.pop()
                #    societe = ".".join(d).upper()
                res.append({
                    'id' : id_seq, 
                    'display_name':i['displayName'],
                    'first_name' : computed_fname,
                    'last_name' : computed_lname,
                    'email' : mail["address"],
                    })
                id_seq += 1
        return res
 
class tazResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _msgraph_people(self):
        tk = self.oauth_access_token
        if not self.oauth_provider_id or not tk or 'microsoft' not in self.oauth_provider_id.data_endpoint:
            return []
        #TODO : raise error if user provider in not microsoft

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
