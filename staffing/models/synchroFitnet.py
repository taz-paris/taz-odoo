import requests
import zlib
import os
import json

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
          
import logging
_logger = logging.getLogger(__name__)
          
##################################################################
##########                SET PARAMETERS                ##########
##################################################################

proto = "https://"
host = "tasmane.fitnetmanager.com"
api_root = "/FitnetManager/rest/"

cache_mode = True
cache_folder = '/tmp/'

##################################################################
##########                 REST CLIENT                  ##########
##################################################################
class ClientRestFitnetManager:
    def __init__(self,proto, host, api_root, login_password):
        self.proto = proto
        self.host = host
        self.api_root = api_root
        self.login_password = login_password
        url_appel_api = proto+host+api_root
        self.url_appel_api = url_appel_api
        _logger.info("ClientRestFitnetManager : " + self.url_appel_api)

    def get_api(self, target_action, read_cache=True):
        if cache_mode :
            path = os.path.join(cache_folder, target_action.replace('/','_'))
            if read_cache :
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as cf:
                        return json.loads(cf.read())

        headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Authorization' : "Basic "+self.login_password,
            'Accept': 'application/json',
            'Host': self.host,
            #'Connection': 'Keep-Alive',
            'User-Agent': '007',
        }
        response = requests.get(self.url_appel_api+target_action, headers=headers)
        response_code = response.status_code
        _logger.info("Code retour :" + str(response_code))
        #res = response.content.decode('utf-8')
        #j = json.load(res)
        res = response.json()
        if cache_mode :
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=4)
        return res


class fitnetPartner(models.Model):
    _inherit = "res.partner"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetEmployee(models.Model):
    _inherit = "hr.employee"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetProject(models.Model):
    _inherit = "project.project"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

    def synchAllFitnet(self):
        login_password = self.env['ir.config_parameter'].sudo().get_param("fitnet_login_password") 
        client = ClientRestFitnetManager(proto, host, api_root, login_password)

        self.sync_customers(client)
        self.sync_contracts(client)

    def sync_customers(self, client):
        _logger.info('---- sync_customers')
        customers = client.get_api("customers/1")
        for customer in customers:
            odoo_customer = self.env['res.partner'].search([('fitnet_id', '=', customer['clientId']), ('is_company', '=', True)])
            if len(odoo_customer) > 1 :
                #_logger.info("Plus d'un res.partner pour cet id client fitnet")
                continue
            if len(odoo_customer) == 0:
                odoo_customer = self.env['res.partner'].search([('ref', '=ilike', customer['clientCode']), ('is_company', '=', True), ('fitnet_id', '=', False)])
                if len(odoo_customer) > 1 :
                    #_logger.info("Plus d'un res.partner pour cet ref %s" % customer['clientCode'])
                    continue
                if len(odoo_customer) == 0:
                    odoo_customer = self.env['res.partner'].search([('name', '=ilike', customer['clientCode']), ('is_company', '=', True), ('fitnet_id', '=', False)])
                    if len(odoo_customer) > 1 :
                        #_logger.info("Plus d'un res.partner pour ce nom %s" % customer['clientCode'])
                        continue
                    if len(odoo_customer) == 0:
                        _logger.info("Aucun res.partner Odoo pour FitnetID=%s / Fitnet name=%s" % (customer['clientId'], customer['name']))
                        continue
                #get FitnetID
                if odoo_customer.fitnet_id != customer['clientId']:
                    odoo_customer.fitnet_id = customer['clientId']
                    _logger.info("Intégration de l'ID Fitnet pour le res.partner : Odoo ID=%s / Odoo name=%s / FitnetID=%s / Fitnet name=%s" % (odoo_customer.id, odoo_customer.name, customer['clientId'], customer['name']))

            #TODO : importer les autres champs de fitnet
               

    def sync_contracts(self, client):
        _logger.info('---- sync_contracts')
        mapping_fields = {
            'title' : {'odoo_field' : 'name'},
            'customerId' : {'odoo_field' : 'partner_id'},
            }
        odoo_model_name = 'project.project'
        fitnet_objects = client.get_api("contracts/1")
        self.create_overide_by_fitnet_values(odoo_model_name, fitnet_objects, mapping_fields, 'contractId')


    def create_overide_by_fitnet_values(self, odoo_model_name, fitnet_objects, mapping_fields, fitnet_id_fieldname) :
        _logger.info('--- create_overide_by_fitnet_values')
        fitnet_objects = [fitnet_objects[0]]
        for fitnet_object in fitnet_objects: 
            #### chercher l'objet et le créer s'il n'existe pas
            fitnet_id = fitnet_object[fitnet_id_fieldname]
            odoo_objects = self.env[odoo_model_name].search([('fitnet_id', '=', fitnet_id)])
            c = False
            if len(odoo_objects) > 1:
                continue
            if len(odoo_objects) == 1 :
                c = odoo_objects[0]
            if len(odoo_objects) == 0 :
                dic = {}
                dic['fitnet_id'] = fitnet_id
                c = self.env[odoo_model_name].create(dic)
                _logger.info("Create Odoo instance of %s object for fitnet %s=%s" % (odoo_model_name, fitnet_id_fieldname, fitnet_id))
            #if not c:
            #    continue

            models = self.env['ir.model'].search([('model','=',odoo_model_name)])
            _logger.info(len(models))
            if len(models) != 1:
                _logger.info("Objet non trouvé %s." % odoo_model_name)
                continue
            model = models[0]

            #### mise à jour depuis Fitnet
            res = {}
            for fitnet_field_name, odoo_dic in mapping_fields.items():
                _logger.info('fitnet_field_name %s' % fitnet_field_name)
                odoo_field_name = odoo_dic['odoo_field']
                odoo_field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', odoo_field_name)])[0]
                odoo_value = None
                if odoo_field.ttype in ["char", "date", "float", "html", "integer", "text"]  :
                    odoo_value = fitnet_object[fitnet_field_name]
                    if c[odoo_field_name] != odoo_value:
                        res[odoo_field_name] = odoo_value
                if odoo_field.ttype == "many2one" :
                    target_objects = self.env[odoo_field.relation].search([('fitnet_id','=',fitnet_object[fitnet_field_name])])
                    if len(target_objects) == 1 :
                        target_object = target_objects[0]
                        if c[odoo_field_name] != target_object:
                            odoo_value = target_object.id
                            res[odoo_field_name] = odoo_value
                    if len(target_object) == 0 :
                        _logger.info("Erreur : aucun objet %s n'a de fitnet_id valorisé à %s" % (odoo_field.relation, fitnet_object[fitnet_field_name]))
                #écraser la valeur Odoo par la valeur Fitent si elles sont différentes
                if odoo_value is None:
                    _logger.info("Type non géré")
                    continue

            if len(res) > 0:
                _logger.info(str(c.id) + str(res))
                c.write(res)
