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

cache_duration_in_minutes = 60
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

    def delete_element_cache(self, napta_type, napta_id): 
        path = os.path.join(cache_folder, napta_type.replace('/','_'))
        if not(os.path.exists(path)):
            return False

        with open(path, 'r', encoding='utf-8') as cf:
            content = json.loads(cf.read())

        content['data_by_id'].pop(str(napta_id))

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)

        return True



    def empty_cache(self):
        _logger.info("------- empty_cache")
        if not(os.path.exists(cache_folder)):
            return False
        for filename in os.listdir(cache_folder):
            file_path = os.path.join(cache_folder, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
                _logger.info("Remove %s" % str(file_path))
        _logger.info("------- empty_cache TERMINÉ")


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


    def get_change_dic(self, napta_type, attributes, napta_id):
        cache_value = self.read_cache(napta_type, napta_id)
        changes_dic = {}
        if cache_value :
            for attribute_key, attribute_value in attributes.items():
                if str(cache_value['attributes'][attribute_key]) != str(attribute_value):
                    changes_dic[attribute_key] = {'old_value' : cache_value['attributes'][attribute_key], 'new_value' : attribute_value}
        return changes_dic, cache_value



    def patch_api(self, napta_type, attributes, napta_id):
        #if napta_type not in ['timesheet','timesheet_period']:#['timesheet_period', 'timesheet', 'userprojectperiod']:
        #    _logger.info('Pas de mise à jour sur ce type pour éviter de faire trop d\'appels.')
        #    return
        changes_dic, cache_value = self.get_change_dic(napta_type, attributes, napta_id)

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
        _logger.info("PATCH "+self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id))
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

    def delete_api(self, napta_type, odoo_object):
        _logger.info('------ delete API')
        _logger.info("ID odoo object : %s" % str(odoo_object.id))
        napta_id = odoo_object.napta_id

        self.delete_api_raw(napta_type, napta_id)

        odoo_object.napta_id = None
        self.env.cr.commit
        self.delete_element_cache(napta_type, napta_id)
        return

    def delete_api_raw(self, napta_type, napta_id):
        headers = {
            'authorization': 'Bearer '+self.get_access_token(),
            'content-type': 'application/json'
        }
        _logger.info("DELETE "+self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id))
        response = requests.delete(self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id), headers=headers)
        if response.status_code == 429:
            _logger.info("POST 429 too many requests : attente de 60 secondes")
            time.sleep(60)
            response = requests.delete(self.API_URL_BUSINESS_ENDPOINT+napta_type+"/"+str(napta_id), headers=headers)
        _logger.info(response.status_code)


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
        for obj in[]: # ["project.project", "res.partner", "staffing.need", "account.analytic.line", "res.users", "hr.contract"]: #, "hr.job", "project.project.stage"
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
    is_prevent_napta_creation = fields.Boolean("Portage pur (ne remonte pas sur Napta)")
    date_start = fields.Date(readonly=True)
    date = fields.Date(readonly=True)

    @api.model_create_multi
    def create(self, vals):
        #_logger.info('---- MULTI create project from napta_connector')
        projects = super().create(vals)
        for rec in projects:
            if not rec.is_prevent_napta_creation:
                rec.create_update_napta()
        return projects

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if not rec.is_prevent_napta_creation:
                rec.create_update_napta()
        return res

    def unlink(self):
        if self.napta_id :
           raise ValidationError(_("Impossible de supprimer ce projet car il est synchronisé avec Napta.")) 
        return super().unlink()

    def delete_on_napta(self):
        self.ensure_one()
        if not self.napta_id:
           raise ValidationError(_("Impossible de supprimer ce projet sur Napta car son id_napta est inconnu.")) 
        _logger.info('Projet à supprimer de napta %s %s (ID ODOO = %s / NaptaID = %s)' % (self.number, self.name, str(self.id), self.napta_id))
        client = ClientRestNapta(self.env)
        self.is_prevent_napta_creation = True
        client.delete_api('project', self)
        self.env.cr.commit()

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
              "sold_budget" : rec.company_part_amount_initial,
              "target_margin_rate" : round(rec.company_part_marging_rate_initial/100.0,2),
              #"estimated_start_date" : str(rec.date_start) if rec.date_start else None,
              #"estimated_end_date" : str(rec.date) if rec.date else None,
            }

            client.create_update_api('project', attributes, rec)

            # Directeur de mission
            if rec.project_director_employee_id:
                rec.project_director_employee_id.user_id.create_update_napta()
                project_contributors = client.read_cache('project_contributor')
                contributor_link_id = None
                for project_contributor in project_contributors.values():
                    if project_contributor['attributes']['contributor_id'] == str(rec.project_director_employee_id.user_id.napta_id) and project_contributor['attributes']['project_id'] == str(rec.napta_id):
                        contributor_link_id = project_contributor['id']
                if not contributor_link_id :
                    if rec.project_director_employee_id.user_id.napta_id:
                        contributor_link_id = client.post_api('project_contributor', {'contributor_id':rec.project_director_employee_id.user_id.napta_id, 'project_id' : rec.napta_id})['data']['id']
                #On ne supprime pas de Napta les contributors qui ne sont pas/plus DM dans Odoo

    def goto_napta(self):
        if self.napta_id:
            return {
                'type': 'ir.actions.act_url',
                'url': 'https://app.napta.io/projects/%s' % (self.napta_id),
                'target': 'new',
            }
    
    def napta_init_from_odoo(self):
        _logger.info('======== DEMARRAGE napta_init_from_odoo ')

        client = ClientRestNapta(self.env)
        client.empty_cache()


        """
        # RESET des user_history portant les CJM
        users = self.env['res.users'].search([])
        for user in users:
            if not user.napta_id :
                _logger.info("Pas de napta_id pour l'utilisatuer : %s" % user.login)
                continue
            for contract in user.employee_id.contract_ids:
                contract.reset_user_history()
        """

        """
        #supprimer les projets remontés par erreur
        projects = self.env['project.project'].search([], order="number desc")
        for project in projects:
            if not project.napta_id:
                continue
            if project.is_project_to_migrate() :
                _logger.info('projet à migrer %s' % project.number)
                continue
            if project.id in [1148,1374,1150,1337,1373,1372,1371] : #1148 = K4M et autres formations Fitnet POUR 2023 uniquement
                continue
            #projet avec un napta_id qui ne sont pas à migrer
            _logger.info('projet à supprimer de napta %s %s (ID ODOO = %s / NaptaID = %s)' % (project.number, project.name, str(project.id), project.napta_id))
            project.is_prevent_napta_creation = True
            client.delete_api('project', project)
            self.env.cr.commit()
        return
        """

        """
        #Synchro du projet 1148 = K4M et autres formations Fitnet POUR 2023 uniquement
        project = self.env['project.project'].search([('id','=',1148)])[0]
        _logger.info('======== INITIALISATION PROJET %s %s (odoo_id = %s)' % (project.name, project.number, str(project.id)))

        forecast_lines = self.env['account.analytic.line'].search([('date', '>', datetime.date(2023,1,1)), ('category', '=', 'project_forecast'), ('project_id', '=', project.id)], order="date asc")
        forecast_lines.create_update_napta_userprojectperiod()

        timesheet_lines = self.env['account.analytic.line'].search([('date', '>', datetime.date(2023,1,1)), ('category', '=', 'project_employee_validated'), ('project_id', '=', project.id)], order="date asc")
        timesheet_lines.create_update_napta_timesheetperiod()

       
        #Déterminer les projet à remonter sur Napta
        projects = self.env['project.project'].search([], order="number desc")
        for project in projects:
            _logger.info(project.number)
            if not project.is_project_to_migrate() :
                continue
            if not project.partner_id: #TODO à traiter à la main
                _logger.info("Projet sans client sur Odoo : non migré vers Napta  %s %s (odoo_id = %s)"% (project.name, project.number, str(project.id)))
                continue
            #if project.id not in [1260]:
            #    continue
            if project.is_prevent_napta_creation :
                continue

            _logger.info('======== INITIALISATION PROJET %s %s (odoo_id = %s)' % (project.name, project.number, str(project.id)))

            forecast_lines = self.env['account.analytic.line'].search([('category', '=', 'project_forecast'), ('project_id', '=', project.id)], order="date asc")
            forecast_lines.create_update_napta_userprojectperiod()

            timesheet_lines = self.env['account.analytic.line'].search([('category', '=', 'project_employee_validated'), ('project_id', '=', project.id)], order="date asc")
            timesheet_lines.create_update_napta_timesheetperiod()

            if len(forecast_lines) == 0 and len(timesheet_lines) == 0:
                if project.stage_id.id == 1: #importer les projets en opportunité... et qui n'ont dont PAS ENCORE de staffing
                    project.create_update_napta()
        """


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

            # The PATCH method is not allowed for this object : if there is a difference delete existing object dans create the new one
            if rec.napta_id:
                changes_dic, cache_value = client.get_change_dic('timesheet_period', attributes, rec.napta_id)
                if any(x in ['timesheet_id', 'project_id', 'day'] for x in changes_dic.keys()):
                    _logger.info("Impossible de patch un timesheet_period avec les attributs 'timesheet_id', 'project_id', 'day' => Suppression sur Napta (puis recréation)")
                    client.delete_api('timesheet_period', rec)

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
            """
            if not(rec.napta_id):
                for napta_user in napta_user_list.values():
                    if napta_user['attributes']['email'] == rec.login :
                        #TODO : toutes les fonctions qui doivent écrire sur un res.user doivent passer par SUDO car un tasmanien l'ambda n'a pas le droit en écriture sur cet objet
                        rec.sudo().napta_id = napta_user['id']
                        self.env.cr.commit()
            if not(rec.napta_id):
                _logger.info('################### Utilisateur manquant %s' % rec.login)
                continue

            rec.employee_id.job_id.create_update_napta()
            attributes = {
                'email' : rec.login,
                'first_name' : rec.first_name,
                'last_name' : rec.name.upper(),
                'active' : rec.active,
                'user_group_id' : 6, #Consultant - TODO gérer dynamiquement l'affectation
                'user_position_id' : rec.employee_id.job_id.napta_id,
                # TODO 'daily_cost' : ,
                # 'hiring_date' : ,
                # 'first_availability_date' : ,
            }
            if rec.napta_id :
                attributes.pop(user_group_id)
                attributes.pop(user_position_id) #TODO : intégrer le mapping Napta ?
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
        

class naptaHrContract(models.Model):
    _inherit = 'hr.contract'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]

    def reset_user_history(self):
        _logger.info('---- RESET Napta user_history')
        client = ClientRestNapta(self.env)
        for rec in self:
            _logger.info(rec.name)
            if not rec.job_id.napta_id :
                _logger.info("Poste inexistant sur Napta %s pour %s." %(rec.job_id.name, rec.name))
                continue

            user_history_target_list = []

            BEGIN_OF_TIME = datetime.date(2020, 1, 1)
            if rec.date_start >= BEGIN_OF_TIME:
                date_debut = rec.date_start
            else :
                date_debut = BEGIN_OF_TIME

            if rec.date_end:
                date_fin = rec.date_end
            else:
                date_fin = datetime.date(datetime.date.today().year, 12, 31)

            d = date_debut
            while d < date_fin:
                cost_line = rec.job_id._get_daily_cost(d) #TODO : on part du principe que le CJM est valable pour toute l'année... il serait plus propre de parcourir les CJM du grade sur la période du contrat
                daily_cost = 0.0
                if cost_line :
                    daily_cost = cost_line.cost
                start_date = d
 
                attributes = {
                    'business_unit_id' : rec.job_id.department_id.napta_id,
                    'daily_cost' : daily_cost,
                    'location_id' : 1, #Paris TODO : ne plus hardcoder cette valeur
                    'start_date' : str(start_date),
                    'user_id' : rec.employee_id.user_id.napta_id,
                    'user_position_id' : rec.job_id.napta_id,
                }
                user_history_target_list.append(attributes)

                d = d + relativedelta(years=1)

            #On supprimer les user_history existant... même ceux qui sont corrects
                # DELETE renvoie un code 422 si on essaye de supprimer le seul user_history restant d'un utilisatuer => dans l'idéal il faudrait mieux raisonner par délta et ne supprimer/créer que le strict nécessaire 
            for user_history_id, user_history in client.read_cache('user_history').items():
                if str(user_history['attributes']['user_id']) != str(rec.employee_id.user_id.napta_id): #TODO : imparfait => on supprime tous les user history de l'utilisateur... y compris pour les autres contrats
                    continue
                client.delete_api_raw('user_history', user_history_id)

            #On recrée tous les user_history
            for user_history_target in user_history_target_list:
                _logger.info(user_history_target) 
                res = client.post_api('user_history', user_history_target)
                napta_id = res['data']['id']
                user_history_target['napta_id'] = napta_id

    #TODO : surcharger les méthodes CRUD de l'objet hr.cost pour que ça mette à jour les CJM de tous les utilisateteurs Napta qui ont sur ce grade sur la période

class naptaHrDepartment(models.Model):
    _inherit = 'hr.department'
    _sql_constraints = [
        ('napta_id_uniq', 'UNIQUE (napta_id)',  "Impossible d'enregistrer deux objets avec le même Napta ID.")
    ]
    napta_id = fields.Char("Napta ID")
