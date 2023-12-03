########################################################################################
########################################################################################
###########
########### FONCTIONS UTILISÉES POUR INITIALISER LES DONNÉES NAPTA À PARTIR DES DONNÉES 
###########      TAZFORCE EN JUIN 2022.
########### SAUF A INVERSER DES FLUX, CES FONCTIONS NE DEVRAIENT PLUS SERVIR
###########
########################################################################################
########################################################################################


import requests
import math
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
          

class naptaNeed(models.Model):
    _inherit = "staffing.need"

    """
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
    """
class naptaAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    """
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
    """

class naptaResUsers(models.Model):
    _inherit = 'res.users'

    """
    def create_update_napta(self):
        #_logger.info('---- Create or update Napta users')
        client = ClientRestNapta(self.env)
        napta_user_list = client.read_cache('user')
        for rec in self:
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
    """
    def create_update_napta(self):
        #_logger.info('---- Create or update Napta user_position')
        client = ClientRestNapta(self.env)
        for rec in self:
            attributes = {
                'name' : rec.name,
            }
            client.create_update_api('user_position', attributes, rec)
    """ 

class naptaHrContract(models.Model):
    _inherit = 'hr.contract'
    """
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
                cost, cost_line = rec.job_id._get_daily_cost(d) #TODO : on part du principe que le CJM est valable pour toute l'année... il serait plus propre de parcourir les CJM du grade sur la période du contrat
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

                d = datetime.date(d.year+1, 1, 1)

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
    """


class naptaHrLeave(models.Model):
    _inherit = "hr.leave"

    def init_leave_pairing(self):
        _logger.info('---- BATCH Create or update Odoo user_holiday')
        client = ClientRestNapta(self.env)
        user_holiday_list = client.read_cache('user_holiday')
       
        """
        #Init napta_id on existing Odoo leave (previously imported from Fitnet)
        for napta_id, user_holiday in user_holiday_list.items():
            res_user = self.env['res.users'].search([('napta_id', '=', str(user_holiday['attributes']['user_id']))])
            employee = res_user.employee_id

            request_date_from_period = 'am'
            if user_holiday['attributes']['start_date_from_morning'] == False : 
                request_date_from_period = 'pm'
            request_date_to_period = 'pm'
            if user_holiday['attributes']['end_date_until_afternoon'] == False :
                request_date_to_period = 'am'
            l = self.env['hr.leave'].search([
                ('napta_id', '=', False), 
                ('employee_id', '=', employee.id), 
                ('state', 'not in', ['refuse', 'canceled']),
                ('request_date_from', '=', user_holiday['attributes']['start_date']), 
                ('request_date_to', '=', user_holiday['attributes']['end_date']), 
                ('request_date_from_period', '=', request_date_from_period),
                ('request_date_to_period', '=', request_date_to_period),
                ])
            if len(l) == 0:
                _logger.info("Pas de congés pour napta_id=%s" % str(napta_id))
            else :
                _logger.info("Napta_id=%s => odoo_id=%s" % (str(napta_id), str(l.id)))
                _logger.info(l.read())
                l.napta_id = napta_id 

        #Set to Refuse state the 2023 holidays that have not been linked to a napta id (due to date differences between Fitnet and Sylae/Lucca)
        orphan_holidays_2023 = self.env['hr.leave'].search([
                ('napta_id', '=', False),
                ('state', 'not in', ['refuse', 'canceled']),
                ('request_date_from', '>=', datetime.date(2023, 1, 1)),
                ])

        for h in orphan_holidays_2023:
            _logger.info('Désactivation du congés odoo_id=%s' % str(h.id))
            #_logger.info(h.read())
            if h.name:
                h.name += " /// Refusé lors de l'initialisation de l'appairage avec les congés Lucca/Napta"
            else :
                h.name = " /// Refusé lors de l'initialisation de l'appairage avec les congés Lucca/Napta"

            h.action_refuse()
        """

