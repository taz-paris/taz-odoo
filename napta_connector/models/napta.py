import requests
import time
import zlib
import os
import json
import datetime
from dateutil.relativedelta import relativedelta
import pytz
from lxml import etree, html

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)
          
##################################################################
##########                SET PARAMETERS                ##########
##################################################################

API_URL_TOKEN_ENDPOINT = "https://pickyourskills.eu.auth0.com/oauth/token"
API_URL_BUSINESS_ENDPOINT = "https://app.napta.io/api/v1/"

cache_mode = False
cache_folder = '/tmp/'

##################################################################
##########                 REST CLIENT                  ##########
##################################################################
class ClientRestNapta:
    def __init__(self, env):
        self.env = env
        self.CLIENT_ID = self.env['ir.config_parameter'].sudo().get_param("napta_client_id")
        self.CLIENT_SECRET = self.env['ir.config_parameter'].sudo().get_param("napta_client_secret")
        self.API_URL_TOKEN_ENDPOINT = API_URL_TOKEN_ENDPOINT
        self.API_URL_BUSINESS_ENDPOINT = API_URL_BUSINESS_ENDPOINT

    def get_access_token(self):
        access_values = json.loads(self.env['ir.config_parameter'].sudo().get_param("napta_access_values"))
        if 'expires_at' in access_values.keys() :
            if datetime.datetime.fromtimestamp(access_values['expires_at']) >= datetime.datetime.now() :
                #_logger.info(access_values)
                return access_values['access_token']

        data = {
                "grant_type":"client_credentials",
                "client_id":self.CLIENT_ID,
                "client_secret":self.CLIENT_SECRET,
                "audience":"backend"
                }
        headers = { 'content-type': "application/x-www-form-urlencoded" }
        _logger.info("--- Call method to get the access token")
        response = requests.post(self.API_URL_TOKEN_ENDPOINT, data=data, headers=headers)
        _logger.info(response.status_code)
        _logger.info(response.content)
        access_values = response.json()
        access_values['expires_at'] = datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(seconds=access_values['expires_in'] - 10))
        _logger.info(access_values)
        self.env['ir.config_parameter'].sudo().set_param('napta_access_values',json.dumps(access_values))
        return access_values['access_token']

    def create_update_api(self, napta_type, attributes, odoo_object):
        _logger.info('------ create_update_api_api API')
        _logger.info(napta_type)
        _logger.info(attributes)
        _logger.info("ID odoo object : %s" % str(odoo_object.id))
        if odoo_object.napta_id :
            return self.patch_api(napta_type, attributes, odoo_object.napta_id)
        else:
            res = self.post_api(napta_type, attributes)
            odoo_object.napta_id = res['data']['id']
            self.env.cr.commit()
            return res

    def patch_api(self, napta_type, attributes, napta_id):
        if napta_type not in []:#['timesheet_period', 'timesheet', 'userprojectperiod']:
            _logger.info('Pas de mise à jour sur ce type pour éviter de faire trop d\'appels.')
            return
        _logger.info('------ patch API')

        data = {
          "data": {
            "attributes": attributes,
            "type": napta_type,
            "id" : napta_id,
          }
        }
        headers = {
            'authorization': 'Bearer '+self.get_access_token(),
            'content-type': 'application/json'
        }
        _logger.info("PATCH "+self.API_URL_BUSINESS_ENDPOINT+napta_type)
        _logger.info(data)
        response = requests.patch(self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id), json=data, headers=headers)
        if response.status_code == 429:
            _logger.info("429 too many requests : attente de 60 secondes")
            time.sleep(60)
            response = requests.patch(self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id), json=data, headers=headers)
        _logger.info(response.status_code)
        _logger.info(response.content)
        res = response.json()
        return res

    def post_api(self, napta_type, attributes):
        _logger.info('------ post API')
        #_logger.info(napta_type)
        #_logger.info(attributes)

        data = {
          "data": {
            "attributes": attributes,
            "type": napta_type
          }
        }
        headers = {
            'authorization': 'Bearer '+self.get_access_token(),
            'content-type': 'application/json'
        }
        _logger.info("POST "+self.API_URL_BUSINESS_ENDPOINT+napta_type)
        _logger.info(data)
        response = requests.post(self.API_URL_BUSINESS_ENDPOINT+napta_type, json=data, headers=headers)
        if response.status_code == 429:
            _logger.info("429 too many requestis : attente de 60 secondes")
            time.sleep(60)
            response = requests.post(self.API_URL_BUSINESS_ENDPOINT+napta_type, json=data, headers=headers)
            
        _logger.info(response.status_code)
        _logger.info(response.content)
        res = response.json()
        return res


    def get_api(self, napta_type):
        _logger.info('------ get API')
        headers = {
            'authorization': 'Bearer '+self.get_access_token(),
            'content-type': 'application/json'
        }
        params = {
            'page[size]' : 10000,
        }
        _logger.info("GET "+self.API_URL_BUSINESS_ENDPOINT+napta_type)
        response = requests.get(self.API_URL_BUSINESS_ENDPOINT+napta_type, params=params,  headers=headers)
        if response.status_code == 429:
            _logger.info("429 too many requests : attente de 60 secondes")
            time.sleep(60)
            response = requests.get(self.API_URL_BUSINESS_ENDPOINT+napta_type, params=params,  headers=headers)
        _logger.info(response.content)
        return response.json()


class naptaProject(models.Model):
    _inherit = "project.project"
    _sql_constraints = [
        ('napta_id__uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objects avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")
    
    def create_update_napta(self):
        _logger.info('---- Create or update Napta project')
        client = ClientRestNapta(self.env)
        for rec in self:
            if not (rec.partner_id.napta_id):
                rec.partner_id.create_update_napta()    

            attributes = {
              "name": rec.name,
              "description" : rec.description or "",
              "billing_method" : "fixed_price",
              "client_id" : rec.partner_id.napta_id,
              "external_id" : str(rec.id),
            }
            client.create_update_api('project', attributes, rec)

    
    """
    def delete_napta_ids(self):
        for obj in ['staffing.need', 'account.analytic.line']:
            _logger.info('Suppression des napta_id sur les instance de %s' % obj)
            list_obj = self.env[obj].search([('napta_id', '!=', None)])
            for o in list_obj :
                o.write({'napta_id' : None})
    """

    def napta_init_from_odoo(self):
        #self.delete_napta_ids()
        #return

        client = ClientRestNapta(self.env)
        #Déterminer les projet à remonter sur Napta
        projects = self.env['project.project'].search([])


        for project in projects:
            _logger.info(project.number)
            if not project.is_project_to_migrate() :
                continue
            if not project.partner_id: #TODO à traiter à la main
                continue


            forecast_lines = self.env['account.analytic.line'].search([('category', '=', 'project_forecast'), ('project_id', '=', project.id)], order="date asc")
            forecast_lines.create_update_napta_userprojectperiod()

            timesheet_lines = self.env['account.analytic.line'].search([('category', '=', 'project_employee_validated'), ('project_id', '=', project.id)], order="date asc")
            #timesheet_lines.create_update_napta_timesheetperiod()

            if len(forecast_lines) == 0 and len(timesheet_lines) == 0:
                if project.stage_id.id == 1: #importer les projets en opportunité... et qui n'ont dont PAS ENCORE de staffing
                    project.create_update_napta()

            #if len(forecast_lines) > 0 or len(timesheet_lines) > 0:
            #    break


class naptaPartner(models.Model):
    _inherit = "res.partner"
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")

    def create_update_napta(self):
        _logger.info('---- Create or update Napta customer')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
              "name": self.name,
              "external_id" : str(rec.id),
            }
            client.create_update_api('client', attributes,rec)


class naptaNeed(models.Model):
    _inherit = "staffing.need"
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")


    def create_update_napta(self):
        _logger.info('---- Create or update Napta user_project')
        client = ClientRestNapta(self.env)
        for rec in self:
            if not (rec.staffed_employee_id.user_id.napta_id):
                rec.staffed_employee_id.user_id.create_update_napta()

            if not (rec.project_id.napta_id):
                rec.project_id.create_update_napta()

            attributes = {
              "project_id": rec.project_id.napta_id,
              "simulated" : False,
              "user_id" : rec.staffed_employee_id.user_id.napta_id,
            }
            client.create_update_api('user_project', attributes, rec)


class naptaAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")


    def create_update_napta_userprojectperiod(self):
        _logger.info('---- Create or update Napta userprojectperiod')
        client = ClientRestNapta(self.env)
        for rec in self:
            if rec.category != 'project_forecast':
                continue

            if not (rec.staffing_need_id.napta_id):
                rec.staffing_need_id.create_update_napta()
            
            """
            posterior_lines = self.env['account.analytic.line'].search([('staffing_need_id', '=', rec.staffing_need_id.id),('category', '=', 'project_forecast'), ('date', '>', rec.date)], order="date desc")
            if len(posterior_lines) > 0:
                # Si ce n'est pas la feuille de temps la plus récente, la date de fin du staffing est la veille de la date de début de la feuille de temps suivante
                end_date = posterior_lines[0].date - relativedelta(days=1)
            else :
            """
            if True:
                # Si c'est la feuille de temps la plus récente, la date de fin du staffing est le vendredi, ou le dernier jour du mois de la date de cette feuille de temps
                dt = rec.date
                last_day_of_month = (dt + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)
                next_friday = dt + relativedelta(days=4 - dt.weekday())
                end_date = min(last_day_of_month,next_friday)

            if rec.date > end_date:
                #ça veut dire que la date du prévisionnel commence un samedi ou un dimanche => possible sur les cissions entre 2 mois avec plannification auto si le 1er jour du mois est un samedi ou un dimanche (en juillet 23 par exemple)
                continue

            attributes = {
              #"completed":
              "user_project_id" : rec.staffing_need_id.napta_id,
              "start_date" : rec.date.isoformat(),
              "end_date" : end_date.isoformat(),
              "staffed_days" : rec.unit_amount,
            }
            client.create_update_api('userprojectperiod', attributes, rec)

    def create_update_napta_timesheetperiod(self):
        _logger.info('---- Create or update Napta timesheetperiod')
        client = ClientRestNapta(self.env)
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
    
            if not (rec.staffing_need_id.napta_id):
                rec.staffing_need_id.create_update_napta()

            if not (rec.staffing_need_id.staffed_employee_id.user_id.napta_id):
                rec.staffing_need_id.staffed_employee_id.user_id.create_update_napta()

            #################### Génération de la timesheet
            #Aucun objet Odoo ne correspond à l'objet timesheet de Napta
            #il faut commencer par rechercher la timesheet pour ce user_id,year,week s'il on veut le mettre à jour
            year = rec.date.year
            week = int(rec.date.strftime("%V"))
            user_id = rec.staffing_need_id.staffed_employee_id.user_id.napta_id

            timesheet_id = None
            timesheet_list = client.get_api('timesheet')
            for timesheet in timesheet_list['data']:
                ta = timesheet['attributes']
                if int(ta['user_id']) == int(user_id) and int(ta['week']) == int(week) and int(ta['year']) == int(year) :
                    timesheet_id = timesheet['id']

            timesheet_dic = {
                        "user_id" : user_id,
                        "week" : week,
                        "year" : year,
                        "closed" : True,
                    }
            if timesheet_id :
                client.patch_api('timesheet', timesheet_dic, timesheet_id)
            else :
                timesheet_id = client.post_api('timesheet', timesheet_dic)['data']['id']

            ###################### Génération de la timesheet_period
            attributes = {
              "timesheet_id" : timesheet_id,
              "project_id" : rec.staffing_need_id.napta_id,
              "day" : rec.date.weekday()+1,
              "worked_days" : rec.unit_amount,
            }
            client.create_update_api('timesheet_period', attributes, rec)

class naptaResUsers(models.Model):
    _inherit = 'res.users'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")


    def create_update_napta(self):
        _logger.info('---- Create or update Napta users')
        client = ClientRestNapta(self.env)
        napta_user_list = client.get_api('user')
        for rec in self:
            for napta_user in napta_user_list['data']:
                if napta_user['attributes']['email'] == rec.login :
                    rec.napta_id = napta_user['id']
                    self.env.cr.commit()

            attributes = {
                'email' : rec.login,
                'first_name' : rec.first_name,
                'last_name' : rec.name,
                'active' : rec.active,
                'user_group_id' : 6, #Consultant - TODO gérer dynamiquement l'affectation
                'user_position_id' : rec.employee_id.job_id.napta_id,
            }
            client.create_update_api('user', attributes, rec)


class naptaJob(models.Model):
    _inherit = 'hr.job'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")

    def create_update_napta(self):
        _logger.info('---- Create or update Napta user_position')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
                'name' : rec.name,
            }
            client.create_update_api('user_position', attributes, rec)
"""
    def synchAllFitnet(self):
        _logger.info(' ############## Début de la synchro Napta')
        login_password = self.env['ir.config_parameter'].sudo().get_param("fitnet_login_password") 
        client = ClientRestFitnetManager(proto, host, api_root, login_password)
        _logger.info(' ############## Fin de la synchro Napta')

    def sync_contracts(self, client):
        _logger.info('---- sync_contracts')
        mapping_fields = {
            'title' : {'odoo_field' : 'name'},
            'projectId' : {'odoo_field' : 'project_group_id'},
            'customerId' : {'odoo_field' : 'partner_id'},
            'beginDate' : {'odoo_field' : 'date_start'},
            'endDate' : {'odoo_field' : 'date'},
            'contractNumber' : {'odoo_field' : 'number'},
            'contractAmount' : {'odoo_field' : 'order_amount'},
            'is_purchase_order_received' : {'odoo_field' : 'is_purchase_order_received'},
            'contractCategoryId' : {
                'odoo_field' : 'outsourcing', 
                'selection_mapping':
                    {
                        '0' : False,
                        '1' : 'no-outsourcing', #Sans Sous-Traitance
                        '2' : 'direct-paiement-outsourcing', #Sous-Traitance paiement direct
                        '3' : 'outsourcing', #Sous-Traitance paiement Tasmane
                        '4' : 'direct-paiement-outsourcing-company', #Sous-Traitance paiement direct + Tasmane
                        '5' : 'co-sourcing', #Avec Cotraitance
                    },
                },
            'remark' : {'odoo_field' : 'remark'},
        #    'description' : {'odoo_field' : 'description'},
        #   TODO : ajouter le contractType qui porte les accords cadre sur Fitnet
            'orderNumber' : {'odoo_field' : 'purchase_order_number'},
            'billedAmount' : {'odoo_field' : 'billed_amount'},
            'payedAmount' : {'odoo_field' : 'payed_amount'},
            'status' : {'odoo_field' : 'stage_id'},
            'project_director_employee_id' : {'odoo_field' : 'project_director_employee_id'},
            'commercialStatusID' : {
                'odoo_field' : 'probability', 
                'selection_mapping':
                    { 
                        '0' : False,
                        '2' : '30',
                        '3' : '70',
                        '5' : '100',
                        '9' : '0',
                    },
                },
            }
        odoo_model_name = 'project.project'
        fitnet_objects = client.get_api("contracts/1")

        for obj in fitnet_objects:
            # Transco de la liste déroulante Bon de commmande reçu en un booléen sur Odoo
            if self.get_proprieteOnDemand_by_id(obj, "zone_13_key_P_1-S_1")  == "Reçu":
                obj['is_purchase_order_received'] = True
            else:
                obj['is_purchase_order_received'] = False
        

            # Recherche du res.user Odoo qui correspond au DM de la mission
            comList = obj['affectedCommercialsList']
            fitnet_employee_id = None
            if len(comList) == 1 :
                fitnet_employee_id = comList[0]['employeeId'] 
            else :
                if len(comList) > 1 :
                    for commercial in comList:
                        if commercial['fullName'] == obj['contractCreator']:
                            fitnet_employee_id = commercial['employeeId']
                    if fitnet_employee_id == None :
                        fitnet_employee_id = comList[0]['employeeId']
            obj['project_director_employee_id'] = fitnet_employee_id

        self.create_overide_by_fitnet_values(odoo_model_name, fitnet_objects, mapping_fields, 'contractId')


    def get_proprieteOnDemand_by_id(self, fitnet_object, prop_id):
        res = None
        for prop in fitnet_object['proprieteOnDemand']:
            if prop['id'] == prop_id:
                res = prop['value']
        return res

    def create_overide_by_fitnet_values(self, odoo_model_name, fitnet_objects, mapping_fields, fitnet_id_fieldname, context={}, filters=[]) :
        _logger.info('--- create_overide_by_fitnet_values')

        count_last_sql_commit = 0
        for fitnet_object in fitnet_objects: 
            count_last_sql_commit += 1 
            if count_last_sql_commit % 1000 == 0:
                _logger.info('######## SQL COMMIT')
                self.env.cr.commit()
            #### chercher l'objet et le créer s'il n'existe pas
            fitnet_id = fitnet_object[fitnet_id_fieldname]
            filter_list = [('fitnet_id', '=', fitnet_id)] + filters
            odoo_objects = self.env[odoo_model_name].search(filter_list)
            odoo_object = False
            if len(odoo_objects) > 1:
                continue
            if len(odoo_objects) == 1 :
                odoo_object = odoo_objects[0]
                dict_dif = self.prepare_update_from_fitnet_values(odoo_model_name, fitnet_object, mapping_fields, odoo_object)
                if len(dict_dif) > 0:
                    #import copy
                    #old_dict_dif = copy.copy(dict_dif)
                    #dic_old_values = odoo_object.with_context(context).read()[0]
                    #_logger.info("Fitnet object : %s" % str(fitnet_object))
                    _logger.info("Mise à jour de l'objet %s ID= %s (fitnet_id = %s) avec les valeurs de Fitnet %s" % (odoo_model_name, str(odoo_object.id), str(fitnet_id), str(dict_dif)))
                    odoo_object.with_context(context).write(dict_dif)
                    #dic_new_values = odoo_object.with_context(context).read()[0]
                    #_logger.info("Changements apportés :")
                    #for field in old_dict_dif.keys() :
                    #    _logger.info("          > %s : %s => %s" %(field, dic_old_values[field], dic_new_values[field]))
            if len(odoo_objects) == 0 :
                dic = self.prepare_update_from_fitnet_values(odoo_model_name, fitnet_object, mapping_fields)
                dic['fitnet_id'] = fitnet_id
                _logger.info("Creating Odoo instance of %s object for fitnet %s=%s with values %s" % (odoo_model_name, fitnet_id_fieldname, fitnet_id, str(dic)))
                odoo_object = self.env[odoo_model_name].with_context(context).create(dic)
                #_logger.info("Odoo object created, Odoo ID=%s state=%s" % (str(odoo_object.id), odoo_object.state))
                _logger.info("Odoo object created, Odoo ID=%s" % (str(odoo_object.id)))
            #if not c:
            #    continue
        _logger.info('######## FINAL SQL COMMIT')
        self.env.cr.commit()

    def delete_not_found_fitnet_object(self, odoo_model_name, fitnet_objects, fitnet_id_fieldname, context={}, filters=[]) :
        _logger.info('--- delete_not_found_fitnet_object')

        fitnet_id_list = []
        for fitnet_object in fitnet_objects:
            fitnet_id = fitnet_object[fitnet_id_fieldname]
            fitnet_id_list.append(fitnet_id)

        filter_list = [('fitnet_id', '!=', None), ('fitnet_id', 'not in', fitnet_id_list)] + filters
        odoo_objects = self.env[odoo_model_name].search(filter_list)
        _logger.info("Nombre d'objets %s qui portent un ID Fitnet qui n'est plus retourné par l'API Fitnet : %s" % (odoo_model_name, str(len(odoo_objects))))
        for odoo_objet in odoo_objects:
            _logger.info(odoo_objet.read())
            odoo_objet.unlink()
            _logger.info("      > Instance supprimée")

        #odoo_objects_all = self.env[odoo_model_name].search([('fitnet_id', '!=', None)])
        #_logger.info(len(odoo_objects_all))


    def prepare_update_from_fitnet_values(self, odoo_model_name, fitnet_object, mapping_fields, odoo_object=False) :
            #_logger.info('--- prepare_update_from_fitnet_values')
            #### mise à jour depuis Fitnet
            models = self.env['ir.model'].search([('model','=',odoo_model_name)])
            if len(models) != 1:
                _logger.info("Objet non trouvé %s." % odoo_model_name)
                return False
            model = models[0]

            res = {}
            for fitnet_field_name, odoo_dic in mapping_fields.items():
                #_logger.info('fitnet_field_name %s' % fitnet_field_name)
                odoo_field_name = odoo_dic['odoo_field']
                odoo_field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', odoo_field_name)])[0]
                odoo_value = None

                if fitnet_field_name in fitnet_object.keys():
                    fitnet_value = fitnet_object[fitnet_field_name]
                else : 
                    #_logger.info(fitnet_field_name)
                    #_logger.info(fitnet_object)
                    onDemand = self.get_proprieteOnDemand_by_id(fitnet_object, fitnet_field_name)
                    if onDemand is not None:
                        fitnet_value = onDemand
                    else :
                        _logger.info("Champ inexistant dans l'objet dans l'objet Fitnet %s" % fitnet_field_name)

                if odoo_field.ttype in ["char", "html", "text", "date", "datetime", "float", "integer", "boolean", "selection", "monetary", "json"]  :
                    if fitnet_value == None:
                        fitnet_value = False
                    odoo_value = fitnet_value

                    if odoo_field.ttype in ["date"]  :
                        if fitnet_value :
                            odoo_value = datetime.datetime.strptime(fitnet_value, '%d/%m/%Y').date()

                    if odoo_field.ttype in ["datetime"]  :
                        #Fitnet dates are implicitly  in Paris Timezone
                        #Odoo expects dates in UTC format without timezone
                        if fitnet_value:
                            odoo_value = datetime.datetime.strptime(fitnet_value, '%d/%m/%Y %H:%M:%S')
                            local = pytz.timezone("Europe/Paris")
                            local_dt = local.localize(odoo_value, is_dst=None)
                            odoo_value = local_dt.astimezone(pytz.utc)
                            odoo_value = odoo_value.replace(tzinfo=None)


                    if odoo_field.ttype in ["float", "monetary"] :
                        odoo_value = float(fitnet_value)

                    if odoo_field.ttype in ["integer"] :
                        odoo_value = int(fitnet_value)

                    if odoo_field.ttype in ["boolean"] :
                        odoo_value = bool(fitnet_value)

                    if odoo_field.ttype in ["selection"] :
                        odoo_value = odoo_dic['selection_mapping'][str(fitnet_value)]

                    if odoo_field.ttype in ["html"] :
                        if fitnet_value and len(fitnet_value.strip())>0: 
                            #TODO : cette conversion ne donne pas le bon encodage => les commentaires avect des accent sont toujours raffraichis, même si Odoo a déjà la bonne valeur
                            html_fitnet = html.tostring(html.fromstring(fitnet_value)).decode('utf-8')
                            #_logger.info(html_fitnet)
                            odoo_value = html_fitnet

                            #html_fitnet5 = html.tostring(html.fromstring(fitnet_value.encode('utf-8'))).decode('utf-8')
                            #_logger.info(html_fitnet5)
                            #html_fitnet4 = html.tostring(html.fromstring(fitnet_value.encode('utf-8')), encoding='utf-8').decode('utf-8')
                            #_logger.info(html_fitnet4)
                            #html_fitnet3 = html.tostring(html.fromstring(fitnet_value, parser=html.HTMLParser(encoding='utf-8'))).decode('utf-8')
                            #_logger.info(html_fitnet3)
                            #html_fitnet2 = html.tostring(html.fromstring(fitnet_value))
                            #_logger.info(html_fitnet2)

                            #html_odoo =  html.tostring(odoo_object[odoo_field_name])
                            #if html_fitnet == html_odoo:
                            #    odoo_value = odoo_object[odoo_field_name]

                    if odoo_object :
                        if odoo_object[odoo_field_name] != odoo_value:
                            _logger.info(odoo_object[odoo_field_name])
                            _logger.info(odoo_value)
                            res[odoo_field_name] = odoo_value
                    else :
                            res[odoo_field_name] = odoo_value


                if odoo_field.ttype == "many2one" :
                    if fitnet_value == None : #le champ manu2one était valorisé sur Fitnet, mais a été remis à blanc sur Fitnet
                        if odoo_object :
                            if odoo_object[odoo_field_name] :
                                res[odoo_field_name] = False
                        else:
                            res[odoo_field_name] = False
                        continue
                    filter_list = [('fitnet_id','=',fitnet_value)]
                    if odoo_field.relation in ['hr.employee']:
                        tup = ('active', 'in', [True, False])
                        filter_list.append(tup)
                    target_objects = self.env[odoo_field.relation].search(filter_list)
                    if len(target_objects) > 1 :
                        _logger.info("Plusieurs objets Odoo %s ont le fitnet_id %s" % (odoo_field.relation, fitnet_value))
                        continue
                    if len(target_objects) == 1 :
                        target_object = target_objects[0]
                        odoo_value = target_object.id
                        if odoo_object :
                            if odoo_object[odoo_field_name] != target_object:
                                res[odoo_field_name] = odoo_value
                        else :
                            res[odoo_field_name] = odoo_value
                    if len(target_objects) == 0 :
                        _logger.info("Erreur : aucun objet %s n'a de fitnet_id valorisé à %s" % (odoo_field.relation, fitnet_value))
                        continue
                #écraser la valeur Odoo par la valeur Fitnet si elles sont différentes
                if odoo_value is None:
                    _logger.info("Type %s non géré pour le champ Fitnet %s = %s" % (odoo_field.ttype, fitnet_field_name, fitnet_value))
                    continue

            return res
"""
