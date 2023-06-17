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

cache_duration_in_minutes = 15
cache_folder = '/tmp/napta'

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
        #_logger.info('------ create_update_api_api API')
        #_logger.info("ID odoo object : %s" % str(odoo_object.id))

        if odoo_object.napta_id :
            return self.patch_api(napta_type, attributes, odoo_object.napta_id)
        else:
            res = self.post_api(napta_type, attributes)
            odoo_object.napta_id = res['data']['id']
            self.env.cr.commit()
            return res

    def read_cache(self, napta_type, napta_id=None):
        if not(os.path.exists(cache_folder)):
            os.mkdir(cache_folder)
        path = os.path.join(cache_folder, napta_type.replace('/','_'))

        if not(os.path.exists(path)) or (datetime.datetime.fromtimestamp(os.path.getmtime(path)) < (datetime.datetime.now() - datetime.timedelta(minutes=cache_duration_in_minutes))) :
            _logger.info('Refresh du cache : objet=%s' % (str(napta_type)))
            api_get_result = self.get_api(napta_type)
            api_get_result_dic = {}
            for obj in api_get_result['data']:
                api_get_result_dic[obj['id']] = obj
            api_get_result['data_by_id'] = api_get_result_dic

            api_get_result.pop('data')

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(api_get_result, f, indent=4)

        with open(path, 'r', encoding='utf-8') as cf:
            object_dic = json.loads(cf.read())['data_by_id']

        if napta_id:
            if napta_id in object_dic.keys():
                return object_dic[napta_id]
            else :
                _logger.info('Absent du cache : objet=%s napta_id=%s' % (str(napta_type), str(napta_id)))
                return False
        else :
            return object_dic


    def update_cache(self, napta_type, napta_id, new_obj):
        path = os.path.join(cache_folder, napta_type.replace('/','_'))
        if not(os.path.exists(path)):
            return False

        with open(path, 'r', encoding='utf-8') as cf:
            content = json.loads(cf.read())
        
        content['data_by_id'][napta_id] = new_obj['data']

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)

        return True

    def empty_cache(self):
        _logger.info("------- empty_cache")
        for filename in os.listdir(cache_folder):
            file_path = os.path.join(cache_folder, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
                _logger.info("Remove %s" % str(file_path))
        _logger.info("------- empty_cache TERMINÉ")


    def patch_api(self, napta_type, attributes, napta_id):
        #if napta_type not in ['timesheet','timesheet_period']:#['timesheet_period', 'timesheet', 'userprojectperiod']:
        #    _logger.info('Pas de mise à jour sur ce type pour éviter de faire trop d\'appels.')
        #    return
        cache_value = self.read_cache(napta_type, napta_id)
        changes_dic = {}
        if cache_value :
            for attribute_key, attribute_value in attributes.items():
                if str(cache_value['attributes'][attribute_key]) != str(attribute_value):
                    changes_dic[attribute_key] = {'old_value' : cache_value['attributes'][attribute_key], 'new_value' : attribute_value}

        if len(changes_dic) == 0:
            #_logger.info('      > Pas de changement.')
            return cache_value

        _logger.info('------ patch API')
        _logger.info(napta_type)
        _logger.info(attributes)
        _logger.info(changes_dic)

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
        self.update_cache(napta_type, napta_id, res)
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
            _logger.info("POST 429 too many requests : attente de 60 secondes")
            time.sleep(60)
            response = requests.post(self.API_URL_BUSINESS_ENDPOINT+napta_type, json=data, headers=headers)
            
        _logger.info(response.status_code)
        _logger.info(response.content)
        res = response.json()
        self.update_cache(napta_type, res['data']['id'], res)
        return res


    def get_api(self, napta_type, page_size=1000000, filter=None):
        """ 
        #Exemple de format du dictionnaire FILTER
        filter=[
            {"name" : "project_id", "op" : "eq", "val" : "127"},
            {"name" : "timesheet_id", "op" : "eq", "val" : "149"},
            {"name" : "day", "op" : "eq", "val" : "1"},
            ]))
            """

        #_logger.info('------ get API')
        headers = {
            'authorization': 'Bearer '+self.get_access_token(),
            'content-type': 'application/json'
        }
        params = {
            'page[size]' : page_size,
        }
        if filter :
            params['filter'] = json.dumps(filter)

        _logger.info("GET "+self.API_URL_BUSINESS_ENDPOINT+napta_type)
        response = requests.get(self.API_URL_BUSINESS_ENDPOINT+napta_type, params=params,  headers=headers)
        if response.status_code == 429:
            _logger.info("GET 429 too many requests : attente de 60 secondes")
            time.sleep(60)
            response = requests.get(self.API_URL_BUSINESS_ENDPOINT+napta_type, params=params,  headers=headers)
        #_logger.info(response.content)
        return response.json()


    """
    def delete_napta_ids(self):
        for obj in [‘project.project’, ‘res.partner’, ‘staffing.need’, ‘account.analytic.line’, ‘res.users’, ‘hr.job’, 'project.project.stage']:
            _logger.info('Suppression des napta_id sur les instance de %s' % obj)
            list_obj = self.env[obj].search([('napta_id', '!=', None)])
            for o in list_obj :
                o.write({'napta_id' : None})
    """



class naptaProject(models.Model):
    _inherit = "project.project"
    _sql_constraints = [
        ('napta_id__uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objects avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")
    
    def create_update_napta(self):
        #_logger.info('---- Create or update Napta project')
        client = ClientRestNapta(self.env)
        for rec in self:
            rec.partner_id.create_update_napta()
            rec.stage_id.create_update_napta()

            attributes = {
              "name": "[%s] %s" % (rec.number or "", rec.name or ""),
              "projectstatus_id" : rec.stage_id.napta_id,
              "description" : rec.description or "",
              "billing_method" : "fixed_price",
              "client_id" : rec.partner_id.napta_id,
              "external_id" : str(rec.id),
              "sold_budget" : rec.company_part_amount_curent,
              "target_margin_rate" : rec.company_part_marging_rate_curent,
              "estimated_start_date" : str(rec.date_start),
              "estimated_end_date" : str(rec.date),
            }
            client.create_update_api('project', attributes, rec)

            # Directeur de mission
            if rec.project_director_employee_id:
                project_contributors = client.read_cache('project_contributor')
                contributor_link_id = None
                for project_contributor in project_contributors.values():
                    if project_contributor['attributes']['contributor_id'] == str(rec.project_director_employee_id.user_id.napta_id) and project_contributor['attributes']['project_id'] == str(rec.napta_id):
                        contributor_link_id = project_contributor['id']
                if not contributor_link_id :
                    contributor_link_id = client.post_api('project_contributor', {'contributor_id':rec.project_director_employee_id.user_id.napta_id, 'project_id' : rec.napta_id})['data']['id']
                #On ne supprime pas de Napta les contributors qui ne sont pas/plus DM dans Odoo

    
    def napta_init_from_odoo(self):
        _logger.info('======== DEMARRAGE napta_init_from_odoo ')

        client = ClientRestNapta(self.env)
        client.empty_cache()
        
        #client.delete_napta_ids()
        #return

        #Déterminer les projet à remonter sur Napta

        projects = self.env['project.project'].search([], order="number desc")

        for project in projects:
            _logger.info(project.number)
            if not project.is_project_to_migrate() :
                continue
            if not project.partner_id: #TODO à traiter à la main
                _logger.info("Projet sans client sur Odoo : non migré vers Napta  %s %s (odoo_id = %s)"% (project.name, project.number, str(project.id)))
                continue
            #if project.id not in [570]:#Hélios
            #    continue

            _logger.info('======== INITIALISATION PROJET %s %s (odoo_id = %s)' % (project.name, project.number, str(project.id)))

            forecast_lines = self.env['account.analytic.line'].search([('category', '=', 'project_forecast'), ('project_id', '=', project.id)], order="date asc")
            forecast_lines.create_update_napta_userprojectperiod()

            timesheet_lines = self.env['account.analytic.line'].search([('category', '=', 'project_employee_validated'), ('project_id', '=', project.id)], order="date asc")
            timesheet_lines.create_update_napta_timesheetperiod()

            if len(forecast_lines) == 0 and len(timesheet_lines) == 0:
                if project.stage_id.id == 1: #importer les projets en opportunité... et qui n'ont dont PAS ENCORE de staffing
                    project.create_update_napta()

        _logger.info('======== napta_init_from_odoo TERMINEE')


class naptaPartner(models.Model):
    _inherit = "res.partner"
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")

    def create_update_napta(self):
        #_logger.info('---- Create or update Napta customer')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
              "name": self.name,
              "external_id" : str(rec.id),
            }
            client.create_update_api('client', attributes,rec)

class naptaProjectStage(models.Model):
    _inherit = "project.project.stage"
    _sql_constraints = [
        ('napta_id__uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objects avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")

    def create_update_napta(self):
        #_logger.info('---- Create or update Napta project stage')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
              "name": rec.name,
            }
            client.create_update_api('projectstatus', attributes, rec)


class naptaNeed(models.Model):
    _inherit = "staffing.need"
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")


    def create_update_napta(self):
        #_logger.info('---- Create or update Napta user_project')
        client = ClientRestNapta(self.env)
        for rec in self:
            rec.staffed_employee_id.user_id.create_update_napta()
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
        ('napta_id_uniq', 'UNIQUE (napta_id, category)',  "Impossible d'enregistrer deux objets account.analytic.line avec le même couple {Napta ID, category}.")
        # ATTENTION : le pointé et le préviionnel sont deux objets sur Napta => donc c'est la clé composée qui est unique. ==> Quels impacts sur le futur ? TODO
    ]
    napta_id = fields.Char("Napta ID")


    def create_update_napta_userprojectperiod(self):
        #_logger.info('---- Create or update Napta userprojectperiod')
        client = ClientRestNapta(self.env)
        for rec in self:
            if rec.category != 'project_forecast':
                continue

            rec.staffing_need_id.create_update_napta()
            
            # La date de fin du staffing est le vendredi, ou le dernier jour du mois de la date de cette feuille de temps
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
        #_logger.info('---- Create or update Napta timesheetperiod')
        client = ClientRestNapta(self.env)
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
    
            rec.staffing_need_id.create_update_napta()
            rec.staffing_need_id.staffed_employee_id.user_id.create_update_napta()

            #################### Génération de la timesheet
            #Aucun objet Odoo ne correspond à l'objet timesheet de Napta
            #il faut commencer par rechercher la timesheet pour ce user_id,year,week s'il on veut le mettre à jour
            year = rec.date.year
            week = int(rec.date.strftime("%V"))
            user_id = rec.staffing_need_id.staffed_employee_id.user_id.napta_id

            timesheet_id = None
            timesheet_list = client.read_cache('timesheet')
            for timesheet in timesheet_list.values():
                ta = timesheet['attributes']
                if int(ta['user_id']) == int(user_id) and int(ta['week']) == int(week) and int(ta['year']) == int(year) :
                    timesheet_id = timesheet['id']

            timesheet_dic = {
                        "user_id" : user_id,
                        "week" : week,
                        "year" : year,
                        "closed" : False,
                    }
            if timesheet_id :
                client.patch_api('timesheet', timesheet_dic, timesheet_id)
            else :
                #_logger.info("ID Odoo %s" % str(rec.id))
                timesheet_id = client.post_api('timesheet', timesheet_dic)['data']['id']

            ###################### Génération de la timesheet_period
            attributes = {
              "timesheet_id" : timesheet_id,
              "project_id" : rec.staffing_need_id.project_id.napta_id,
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
        #_logger.info('---- Create or update Napta users')
        client = ClientRestNapta(self.env)
        napta_user_list = client.read_cache('user')
        for rec in self:
            if not(rec.napta_id):
                for napta_user in napta_user_list.values():
                    if napta_user['attributes']['email'] == rec.login :
                        rec.napta_id = napta_user['id']
                        self.env.cr.commit()

            """
            rec.employee_id.job_id.create_update_napta()
            attributes = {
                'email' : rec.login,
                'first_name' : rec.first_name,
                'last_name' : rec.name,
                'active' : rec.active,
                'user_group_id' : 6, #Consultant - TODO gérer dynamiquement l'affectation
                'user_position_id' : rec.employee_id.job_id.napta_id,
                # TODO 'daily_cost' : ,
                # 'hiring_date' : ,
                # 'first_availability_date' : ,
            }
            client.create_update_api('user', attributes, rec)
            """


class naptaJob(models.Model):
    _inherit = 'hr.job'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")

    def create_update_napta(self):
        #_logger.info('---- Create or update Napta user_position')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
                'name' : rec.name,
            }
            client.create_update_api('user_position', attributes, rec)

