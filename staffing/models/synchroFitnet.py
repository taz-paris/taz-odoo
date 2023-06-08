import requests
import zlib
import os
import json
import datetime
import pytz
from lxml import etree, html

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
          
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)
          
##################################################################
##########                SET PARAMETERS                ##########
##################################################################

proto = "https://"
host = "tasmane.fitnetmanager.com"
api_root = "/FitnetManager/rest/"

cache_mode = False
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

    def get_api(self, target_action):
        path = os.path.join(cache_folder, target_action.replace('/','_'))
        if cache_mode :
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
        _logger.info("Calling "+ self.url_appel_api+target_action)
        response = requests.get(self.url_appel_api+target_action, headers=headers)
        response_code = response.status_code
        _logger.info("HTTP return code :" + str(response_code))
        res = response.json()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=4)
        return res


class fitnetPartner(models.Model):
    _inherit = "res.partner"
    _sql_constraints = [
        ('fitnet_id_uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetProjectStage(models.Model):
    _inherit = "project.project.stage"
    _sql_constraints = [
        ('fitnet_id_uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetEmployee(models.Model):
    _inherit = "hr.employee"
    _sql_constraints = [
        ('fitnet_id_uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _sql_constraints = [
        ('fitnet_id_uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetNeed(models.Model):
    _inherit = "staffing.need"
    _sql_constraints = [
        ('fitnet_id_uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objets avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetLeave(models.Model):
    _inherit = "hr.leave"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetLeaveType(models.Model):
    _inherit = "hr.leave.type"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetAccountMove(models.Model):
    _inherit = "account.move"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetAccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetBankAccount(models.Model):
    _inherit = "res.partner.bank"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetJob(models.Model):
    _inherit = "hr.job"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

class fitnetHrContract(models.Model):
    _inherit = "hr.contract"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")


class fitnetProjectGroup(models.Model):
    _inherit = "project.group"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")


class fitnetProjectGroup(models.Model):
    _inherit = "account.payment"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")


class fitnetProjectGroup(models.Model):
    _inherit = "account.journal"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")





class fitnetProject(models.Model):
    _inherit = "project.project"
    _sql_constraints = [
        ('fitnet_id__uniq', 'UNIQUE (fitnet_id)',  "Impossible d'enregistrer deux objects avec le même Fitnet ID.")
    ]
    fitnet_id = fields.Char("Fitnet ID")

    def import_grille_competences(self):
        file_path = '/home/ubuntu/230122_Grille_competences.csv'
        with open(file_path, 'r', encoding="utf-8") as f :
            import csv
            csvreader = csv.DictReader(f, delimiter=';')
            for row in csvreader:
                #print(row)
                employees = self.env['hr.employee'].search([('first_name', '=', row['prénom']), ('name', '=', row['Nom']), ('work_email', '!=', False)])
                if len(employees) != 1:
                    print("Erreur pour trouver l'employee %s" % row['Nom'])
                    print(employees)
                    continue
                employee = employees[0]
                print('--- Compétences de l\'employee %s' % row['Nom'])

                for skill_name, skill_value in row.items():
                    if skill_name in ["", "Nom", "prénom", "Date de mise à jour"]:
                        continue
                    skills = self.env['hr.skill'].search([('name', '=', skill_name)])
                    if len(skills) != 1:
                        print("Erreur pour trouver la skill %s" % skill_name)
                        print(skills)
                        continue
                    skill = skills[0]

                    if skill_value == '':
                        skill_level_name = "Je ne connais pas du tout"
                    elif skill_value in ['x', 'X']:
                        skill_level_name = 'OUI'
                    elif skill_value in ['1', '2', '3', '4']:
                        skill_level_name = 'Niveau %s' % skill_value
                    else :
                        print("Erreur : donnée inatendue dans la grille Excel pour le niveau %s pour la compétence %s" % (skill_value, skill_name))
                        continue
                    levels = self.env['hr.skill.level'].search([('skill_type_id', '=', skill.skill_type_id.id), ('name', '=', skill_level_name)])
                    if len(levels) != 1:
                        print("Erreur pour trouver le niveau %s pour la compétence %s" % (skill_value, skill_name))
                        print(levels)
                        continue
                    level = levels[0]


                    employee_skills = self.env['hr.employee.skill'].search([('employee_id', '=', employee.id), ('skill_id', '=', skill.id)])
                    if len(employee_skills) > 1:
                        print("Erreur : il y a plus d'une hr.employee.skill pour la compétence %s pour %s" % (skill.id, employee.name))
                        print(employee_skills)
                    elif len(employee_skills) == 1:
                        #mise à jour
                        employee_skill = employee_skills[0]
                        if employee_skill.skill_level_id.id != level.id :
                            print("Mise a jour de la compétence %s au niveau %s pour %s" % (skill.name, level.name, employee.name))
                            employee_skill.skill_level_id = level.id
                    else :
                        #creation
                        print("Créaion de la compétence %s au niveau %s pour %s" % (skill.name, level.name, employee.name))
                        self.env['hr.employee.skill'].create({'employee_id' : employee.id, 'skill_id' : skill.id, 'skill_level_id' : level.id, 'skill_type_id' : skill.skill_type_id.id})



    def synchAllFitnet(self):
        _logger.info(' ############## Début de la synchro Fitnet')
        login_password = self.env['ir.config_parameter'].sudo().get_param("fitnet_login_password") 
        client = ClientRestFitnetManager(proto, host, api_root, login_password)


        self.sync_supplier_invoices(client)
        self.sync_customer_invoices(client)
        self.sync_suppliers(client)

        self.sync_customers(client)
        #TODO           self.sync_prospect(client)

        #return self.import_grille_competences()
        self.sync_employees(client)
        self.sync_employees_contracts(client)

        self.sync_holidays(client) 
        self.correct_leave_timesheet_stock(client)

        self.sync_project(client)
        self.sync_contracts(client)

        self.sync_assignments(client)
        self.sync_assignmentsoffContract(client)
    
        self.sync_timesheets(client)

        #Correctif à passer de manière exceptionnelle
        #self.analytic_line_employee_correction()
        

        #TODO : gérer les mises à jour de congés (via sudo() ?) avec des demandes au statut validé
        _logger.info(' ############## Fin de la synchro Fitnet')

    def correct_leave_timesheet_stock(self, client):
        _logger.info('---- correct_leave_timesheet_stock')
        leaves = self.env['hr.leave'].search([('fitnet_id', '!=', None), ('state', '=', "validate"), ('request_date_from', '>', '2022-12-31')]) 
        for leave in leaves:
            count = 0.0
            timesheets = self.env['account.analytic.line'].search([('holiday_id', '=', leave.id)])
            for timesheet in timesheets:
                count += timesheet.unit_amount
            if count != leave.number_of_days:
                _logger.info('Incohérence : leave_id=%s pour %s (statut : %s) => duréee =%s alors que total des timesheet=%s. Debut le %s' % (str(leave.id), leave.employee_id.name, leave.state, str(leave.number_of_days), str(count), str(leave.request_date_from)))
                _logger.info('      Créé le %s Dernière modif du congés : %s' % (str(leave.create_date), str(leave.write_date)))
                #leave.number_of_days = leave.number_of_days
                #_logger.info('      Corrigé')

    def sync_holidays(self, client):
        _logger.info('---- sync_holydays')

        # RESET analytics lines
        #leaves = self.env['hr.leave'].search([])
        #for l in  leaves:
        #    if l.state not in ['refuse', 'canceled'] :
        #        l._validate_leave_request()
        #return False

        odoo_model_name = 'hr.leave'
        fitnet_leave_contents = {}

        period_list = []

        #for year in range(2020, 2025):
        #    for month in range(1,13):
        #       period_list.append((month, year))

        for i in [-1, 0, 1, 2, 3, 4, 5, 6]: #on synchronise les congés du mois précédent, du mois en cours et des 6 prochain moins
            t = datetime.datetime.today() + relativedelta(months=i)
            period_list.append((t.month, t.year))

        for month, year in period_list :
                _logger.info('Get leaves for %s/%s' % (str(month), str(year)))
                fitnet_objects = client.get_api('leaves/getLeavesWithRepartition/1/%s/%s' % (month, year))
                #_logger.info(fitnet_objects)
                #_logger.info(type(fitnet_objects))
                if isinstance(fitnet_objects, list) : #this id False when there is no leaves for a month
                    _logger.info("Nombre de congés au moins en partie sur ce mois : %s" % len(fitnet_objects))
                    for obj in fitnet_objects:
                        for leaveType in obj['leaveTypes']:
                            #if leaveType['id'] not in [992]: #992 : 3.5 RTT de Takoua a partir du 28/12/202
                            #    continue
                            #_logger.info("Adding leaveType ID=%s" % str(leaveType['id']))
                            #leaveType['master_fitnet_leave_id'] = obj['leaveId']
                            leaveType['designation'] = obj['designation']
                            leaveType['employeeId'] = obj['employeeId']
                            leaveType['status'] = obj['status']
                            if leaveType['startMidday'] == True:
                                leaveType['request_date_from_period'] = 'pm'
                                beginHour = '13:00:00'
                            else :
                                leaveType['request_date_from_period'] = 'am'
                                beginHour = '00:00:01'
                            if leaveType['endMidday'] == True:
                                leaveType['request_date_to_period'] = 'am'
                                endHour = '13:00:00'
                            else :
                                leaveType['request_date_to_period'] = 'pm'
                                endHour = '23:59:59'
                            leaveType['beginDateTime'] = leaveType['beginDate'] + ' ' + beginHour
                            leaveType['endDateTime'] = leaveType['endDate'] + ' ' + endHour
                            fitnet_leave_contents[leaveType['id']] = leaveType

        mapping_fields = {
            'designation' : {'odoo_field' : 'notes'},
            'employeeId' : {'odoo_field' : 'employee_id'},
            'typeId' : {'odoo_field' : 'holiday_status_id'},
            'beginDate' : {'odoo_field' : 'request_date_from'},
            'endDate' : {'odoo_field' : 'request_date_to'},
            'beginDateTime' : {'odoo_field' : 'date_from'},
            'endDateTime' : {'odoo_field' : 'date_to'},
            'numberOfDays' : {'odoo_field' : 'number_of_days'},
            'request_date_from_period' : {'odoo_field' : 'request_date_from_period', 'selection_mapping' : {'am' : 'am', 'pm':'pm'}},
            'request_date_to_period' : {'odoo_field' : 'request_date_to_period', 'selection_mapping' : {'am' : 'am', 'pm':'pm'}},
            'status' : {'odoo_field' : 'state', 'selection_mapping' : {'Demande accordée' : 'validate', 'Demande annulée' : 'canceled', 'Demande refusée' : 'refuse', 'False' : 'draft', '900':'confirm', 'Demande' : 'validate'}},
            }
        _logger.info(len(fitnet_leave_contents.values()))
        with open('/tmp/old_all_leaves', 'w', encoding='utf-8') as f:
            json.dump(fitnet_leave_contents, f, indent=4)
        values = fitnet_leave_contents.values()

        #TODO : bizarre : quand on passer un state qui n'est pas validate, à la création il est surchargé par validate... alors qu'il est bien remplacé par le statut demandé si execute à nouveau le script
        self.create_overide_by_fitnet_values(odoo_model_name, values, mapping_fields, 'id',context={'leave_skip_date_check':True})



    def sync_timesheets(self, client):
        _logger.info('---- sync_timesheets')
        #fitnet_objects = client.get_api("activities/getActivitiesOnContract/1/01-01-2018/01-01-2050") #=> endpoint unitile : il ne comporte pas l'assignementID
        fitnet_objects = client.get_api("timesheet/timesheetAssignment?companyId=1&startDate=01-01-2018&endDate=01-06-2050")
        fitnet_filtered = []
        for obj in fitnet_objects:
            if obj['activityType'] == 3:
                #Activity type: 1:Contracted activity, 2:Off-Contract activity, 3:Training 
                continue

            assignmentID = obj['assignmentID']
            if obj['activityType'] == 2:
                assignmentID = 'assignmentOffContractID_'+str(obj['assignmentID'])


            if obj['amount'] != 0.0 : 
                validated_line = {
                        'assignmentID' : assignmentID,
                        'category' : 'project_employee_validated',
                        'amount' : obj['amount'],
                        'assignmentDate' : obj['assignmentDate'],
                        'fitnet_id' : 'validated_timesheet_' + str(obj['activityType']) + '_' + str(obj['timesheetAssignmentID']),
                        }
                fitnet_filtered.append(validated_line)

            if obj['forecastedAmount'] != 0.0 :
                forecast_line = {
                        'assignmentID' : assignmentID,
                        'category' : 'project_forecast',
                        'amount' : obj['forecastedAmount'],
                        'assignmentDate' : obj['assignmentDate'],
                        'fitnet_id' : 'forecast_timesheet_' + str(obj['activityType']) + '_' + str(obj['timesheetAssignmentID']),
                        }
                fitnet_filtered.append(forecast_line)

        odoo_model_name = 'account.analytic.line'
        mapping_fields = {
            'assignmentID' : {'odoo_field' : 'staffing_need_id'},
            'category' : {'odoo_field' : 'category', 'selection_mapping' : {'project_employee_validated' : 'project_employee_validated', 'project_forecast' : 'project_forecast'}},
            'amount' : {'odoo_field' : 'unit_amount'},
            'assignmentDate' : {'odoo_field' : 'date'},
            }
        self.delete_not_found_fitnet_object(odoo_model_name, fitnet_filtered, 'fitnet_id')
        self.create_overide_by_fitnet_values(odoo_model_name, fitnet_filtered, mapping_fields, 'fitnet_id')


    def analytic_line_employee_correction(self):
        #Corriger les affectations d'employee si les hr.employee sont créé a posteriori
        lines = self.env['account.analytic.line'].search([('staffing_need_id', '!=', False)])
        count_last_sql_commit = 0
        for line in lines :
            count_last_sql_commit += 1 
            if count_last_sql_commit % 1000 == 0:
                _logger.info('######## SQL COMMIT')
                self.env.cr.commit()
            line.employee_id =  line.staffing_need_id.staffed_employee_id.id
        _logger.info('######## FINAL SQL COMMIT')
        self.env.cr.commit()

    def sync_assignments(self, client):
        _logger.info('---- sync_assignments')
        fitnet_objects = client.get_api("assignments?companyId=1&startDate=01-01-2018&endDate=31-12-2040")
        for obj in fitnet_objects:
            obj['status'] = 'done'

        mapping_fields = {
            'assignmentStartDate' : {'odoo_field' : 'begin_date'},
            'assignmentEndDate' : {'odoo_field' : 'end_date'},
            'initialBudget' : {'odoo_field' : 'nb_days_needed'},
            'contractID' : {'odoo_field' : 'project_id'}, 
            'employeeID' : {'odoo_field' : 'staffed_employee_id'}, 
            'status' : {'odoo_field' : 'state', 'selection_mapping' : {'done' : 'done'}},
            }
        odoo_model_name = 'staffing.need'
        self.create_overide_by_fitnet_values(odoo_model_name, fitnet_objects, mapping_fields, 'assignmentOnContractID')

    def sync_assignmentsoffContract(self, client):
        _logger.info('---- sync_assignmentsOffContract')
        fitnet_objects = client.get_api("assignments/offContract/1")
        for obj in fitnet_objects:
            obj['status'] = 'done'
            obj['assignmentOffContractID'] = 'assignmentOffContractID_'+str(obj['assignmentOffContractID'])
            obj['offContractActivityID'] = 'offContractActivityID_'+str(obj['offContractActivityID'])
            obj['assignmentStartDate'] = '01/01/2020'

        mapping_fields = {
            'assignmentStartDate' : {'odoo_field' : 'begin_date'},
            #'assignmentEndDate' : {'odoo_field' : 'end_date'},
            #'initialBudget' : {'odoo_field' : 'nb_days_needed'},
            'offContractActivityID' : {'odoo_field' : 'project_id'},
            'employeeID' : {'odoo_field' : 'staffed_employee_id'},
            'status' : {'odoo_field' : 'state', 'selection_mapping' : {'done' : 'done'}},
            }
        odoo_model_name = 'staffing.need'
        self.create_overide_by_fitnet_values(odoo_model_name, fitnet_objects, mapping_fields, 'assignmentOffContractID')

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
                odoo_customer.fitnet_id = customer['clientId']
                _logger.info("Intégration de l'ID Fitnet pour le res.partner : Odoo ID=%s / Odoo name=%s / FitnetID=%s / Fitnet name=%s" % (odoo_customer.id, odoo_customer.name, customer['clientId'], customer['name']))

            #on appelle pas directement create_overide_by_fitnet_values car on ne veut pas créer le client automatiquement (risque de doublonner) s'il n'a pas pu être mappé sur le nom ou la ref 
                # Dans ce cas on veut le le client soit créé manuellement par Denis ou Margaux
            customer['paymentTermsId'] = customer['companyCustomerLink'][0]['paymentTermsId']
            if customer['siret']:
                customer['siret'] = customer['siret'].replace(' ', '').replace('.', '')
            if customer['vatNumber']:
                customer['vatNumber'] = customer['vatNumber'].replace(' ', '').replace('.', '')
            if customer['phone']:
                customer['phone'] = customer['phone'].replace(' ', '')
            if customer['email']:
                customer['email'] = customer['email'].replace(' ', '')
            if customer['clientCode']:
                customer['clientCode'] = customer['clientCode'].replace(' ', '')

            #if customer['vatNumber'] in ['FR59542051180']:
                # TODO : Le numéro TVA intracom de TotalEnergie FR59542051180 produit une boucle infinie lors de l'enregistrement
                    #https://github.com/odoo/odoo/blob/c5be51a5f02471e745543b3acea4f39664f8a820/addons/base_vat/models/res_partner.py#L635    
            #   del customer['vatNumber']

            mapping_fields = {
                'vatNumber' : {'odoo_field' : 'vat'}, 
                'clientCode' : {'odoo_field' : 'ref'},
                'phone' : {'odoo_field' : 'phone'},
                'email' : {'odoo_field' : 'email'},
                'paymentTermsId' : {'odoo_field' : 'property_payment_term_id'},

                'siret' : {'odoo_field' : 'siret'},

                'address_streetNumber' : {'odoo_field' : 'street'},
                'address_additionnalAddressInfo' : {'odoo_field' : 'street2'},
                'address_additionnalAddressInfo2' : {'odoo_field' : 'street3'},
                'address_zipCode' : {'odoo_field' : 'zip'},
                'address_city' : {'odoo_field' : 'city'},
                'default_invoice_payement_bank_account' : {'odoo_field' : 'default_invoice_payement_bank_account'},
                #compte bancaire
                #compte comptable
                #customerGroupId => on ne la synchronise pas car Odoo doit rester maître
                #segmentId => on ne la synchronise pas car Odoo doit rester maître sur le Business Domain (plus à jour que Fitnet)
            }

            

            ####### Compte bancaire de paiement par défault
            customer['default_invoice_payement_bank_account'] = None
            iban = customer['companyCustomerLink'][0]['iban']
            bank_accounts = self.env['res.partner.bank'].search([])
            for ba in bank_accounts:
                if ba.acc_number.replace(' ', '') == iban:
                    customer['default_invoice_payement_bank_account'] = ba.fitnet_id


            ####### Import de l'addresse postale la plus intéressante (difficile de gérer plusieurs addresse, il faudrait un fitnet_address_id sur le res.partner... ce qui ne serait pas compatible avec l'algo de base)
            customer['address_streetNumber'] = None
            customer['address_additionnalAddressInfo'] = None
            customer['address_additionnalAddressInfo2'] = None
            customer['address_zipCode'] = None
            customer['address_city'] = None

            customer_addresses = client.get_api("customerAddress?companyId=1&customerId="+str(customer['clientId']))
            if "No customer addresses found" in json.dumps(customer_addresses):
                _logger.info("Aucune addresse postale dans Fitnet pour %s (Finet_id = %s)" % (odoo_customer.name, str(customer['clientId'])))
            else :
                if len(customer_addresses) != 1 :
                    _logger.info("Le client %s (fitnet_id = %s) a %s addresses postales dans Fitnet." % (odoo_customer.name, str(customer['clientId']), str(len(customer_addresses))))
                target_odoo_address = None
                for address in customer_addresses:
                    if target_odoo_address == None:
                        target_odoo_address = address
                    else :
                       #si Fitnet a un adresse par défaut et une adresse de facturation par défaut, alors on prend l'adresse de facturation par défaut
                       # Cette méthode vise à gérer une qualité de donnée inégale sur Fitnet
                            # - certains clients ont une adresse sur Fitnet mais qui n'est déclarée ni comme par défaut pour Tasmane, ni comme adresse de facturation par défault
                            # - certaines addresse ont une "addresse complète" (format libre) mais les champs structurés ne sont pas rempli
                       if address['isDefaultInvoicingAddress'] :
                           target_odoo_address = address
                           break
                       if address['isDefaultAddress'] :
                           target_odoo_address = address
                if target_odoo_address == None:
                    _logger.info("Aucune addresse postale dans Fitnet pour %s (Finet_id = %s)" % (odoo_customer.name, str(customer['clientId'])))
                else :
                    #customer['address_label'] = target_odoo_address['addressLabel']
                    customer['address_streetNumber'] = target_odoo_address['streetNumber']
                    customer['address_additionnalAddressInfo'] = target_odoo_address['additionnalAddressInfo']
                    customer['address_zipCode'] = target_odoo_address['zipCode']
                    customer['address_city'] = target_odoo_address['city']
                    if target_odoo_address['country'] and target_odoo_address['country'].strip().lower() != "france" :
                        _logger.info("Pays (non FR) fourni pour cette adresse postale %s => Merci de le saisir à la main dans Odoo" % target_odoo_address['completeAddress'])

                    if not(target_odoo_address['zipCode'] and target_odoo_address['city'] and target_odoo_address['streetNumber']):
                        _logger.info("Client %s (fitnet_id = %s). L'un des champs structurés de l'addresse n'est pas fourni pour cette adresse postale (format libre) %s" % (odoo_customer.name, str(customer['clientId']), target_odoo_address['completeAddress']))
                        lines = target_odoo_address['completeAddress'].split("\r\n")
                        cust = odoo_customer.name
                        if lines[0].strip().lower() == cust.strip().lower() :#or lines[0].strip().lower() == odoo_customer.long_company_name.strip().lower():
                            lines.pop(0)
                        if lines[len(lines)-1].strip().lower() == 'france':
                            lines.pop(len(lines)-1)

                        if len(lines) not in [2, 3, 4] :
                            _logger.info("Trop / trop peu de lignes pour une interprétation automatique.")
                        else :
                            city_line = lines.pop(len(lines)-1).strip()
                            if not(city_line[0:5].isdigit()):
                                _logger.info("Cette ligne devrait commencer par un code postal à 5 chiffres : %s" % city_line)
                            else :
                                customer['address_zipCode'] = city_line[0:5]
                                customer['address_city'] = city_line[5:].strip()
                                
                                customer['address_streetNumber'] = lines.pop(0).strip()
                                if len(lines) :
                                    customer['address_additionnalAddressInfo'] = lines.pop(0).strip()
                                if len(lines) :
                                    customer['address_additionnalAddressInfo2'] = lines.pop(0).strip()

                                _logger.info("Addresse transformée : \n%s\n%s\n%s\n%s" % (customer['address_streetNumber'], customer['address_additionnalAddressInfo'], customer['address_zipCode'], customer['address_city']))




            old_odoo_values, res = self.prepare_update_from_fitnet_values('res.partner', customer, mapping_fields, odoo_customer)
            if len(res) > 0:
                _logger.info("Mise à jour du res.partner client Odoo ID= %s avec les valeurs de Fitnet %s" % (str(odoo_customer.id), str(res)))
                odoo_customer.write(res)
 

    def sync_customer_invoices(self, client):
        _logger.info('---- sync_customer_invoices')
        fitnet_objects = client.get_api('invoices/v2/1/0/01-01-2018/31-12-2050')
        mapping_fields_invoice = {
            'invoiceNumber' : {'odoo_field' : 'name'},
            'customerId' : {'odoo_field' : 'partner_id'},
            'billingDate' : {'odoo_field' : 'invoice_date'},
            'invoice_date' : {'odoo_field' : 'invoice_date'},
            'expectedPaymentDate' : {'odoo_field' : 'invoice_date_due'},
            'ibanId' : {'odoo_field' : 'partner_bank_id'},
            'move_type' : {'odoo_field' : 'move_type', 'selection_mapping' : {'out_invoice' : 'out_invoice', 'out_refund':'out_refund'}},
            'referenceInvoiceNumber' : {'odoo_field' : 'invoice_origin'},
            # : {'odoo_field' : 'reversal_move_id'}
            #'odoo_state' : {'odoo_field' : 'state', 'selection_mapping' : {'draft' : 'draft', 'posted':'posted', 'cancel' : 'cancel'}},
            #'odoo_payment_state' : {'odoo_field' : 'payment_state', 'selection_mapping' : { : 'not_paid', : 'in_payment', : 'paid', : 'partial', : 'reversed', : 'invoicing_legacy'}}
        }
        mapping_fields_invoice_line = {
            'inoviceId' : {'odoo_field' : 'move_id'},
            'designation' : {'odoo_field' : 'name'},
            'amountBTax' : {'odoo_field' : 'price_unit'},
            'quantity' : {'odoo_field' : 'quantity'},
            'contractId_json' : {'odoo_field' : 'analytic_distribution'},
            #product_id
        }
        mapping_fields_payment = {
            'partner_id' : {'odoo_field' : 'partner_id'},
            'amount' : {'odoo_field' : 'amount'},
            'date' : {'odoo_field' : 'date'},
            'payment_type' : {'odoo_field' :'payment_type', 'selection_mapping' : {'inbound' : 'inbound', 'outbound' : 'outbound'}},
            'partner_bank_id' : {'odoo_field' : 'partner_bank_id'},
            #'odoo_state' : {'odoo_field' : 'state', 'selection_mapping' : {'draft' : 'draft', 'posted':'posted', 'cancel' : 'cancel'}},
            'journal_id' : {'odoo_field' : 'journal_id'},
            'partner_type' : {'odoo_field' : 'partner_type',  'selection_mapping' : {'customer' : 'customer', 'supplier' : 'supplier'}},
        }
        invoices_list = []
        invoices_lines_list = []
        payment_list = []
        for invoice in fitnet_objects:
            #if invoice['invoiceId'] not in [1492, 1493]:
            #    continue
            #if invoice['status'] not in ["Facture réglée", "Avoir réglé"]:
            #    continue
            if invoice['bTaxBilling'] < 0:
                #_logger.info('avoir fitnet invoiceId=' + str(invoice['invoiceId']))
                #TODO : vérifier que c'est cohérent avec "isCredit": "Yes",
                invoice['move_type'] = 'out_refund'
            else :
                invoice['move_type'] = 'out_invoice'
            invoice['invoice_date'] = invoice['billingDate']
            invoices_list.append(invoice)

            for line in invoice['invoiceLines']:
                line['inoviceId'] = invoice['invoiceId']
                odoo_analytic_ccount_id_project = self.env['project.project'].search([('fitnet_id', '=', invoice['contractId'])])[0].analytic_account_id.id
                line['contractId_json'] = {str(odoo_analytic_ccount_id_project) : 100.0} 
                line['quantity'] = 1.00
                invoices_lines_list.append(line)
                #if line['vatRate'] != 20.0:
                #    raise ValidationError(_("Taux de TVA != 20%"))

            if invoice['actualPaymentDate'] != "" :
                payment = {
                        'paymentId' : 'payment_' + str(invoice['invoiceId']),
                        'inoviceId' : invoice['invoiceId'],
                        'partner_id' : invoice['customerId'],
                        'amount' : "%.2f" % round(abs(invoice['wTaxBilling']),2),
                        'date' : invoice['actualPaymentDate'],
                        'partner_type' : 'customer',
                    }
                if invoice['move_type'] == 'out_invoice' : 
                    payment['payment_type'] = 'inbound'
                elif invoice['move_type'] == 'out_refund' :
                    payment['payment_type'] = 'outbound'
                payment['journal_id'] = invoice['ibanId']
                payment['partner_bank_id'] = invoice['ibanId']
                payment_list.append(payment)

        self.create_overide_by_fitnet_values('account.move', invoices_list, mapping_fields_invoice, 'invoiceId',context={})
        self.create_overide_by_fitnet_values('account.move.line', invoices_lines_list, mapping_fields_invoice_line, 'inoviceLineId',context={})
        """
        self.create_overide_by_fitnet_values('account.payment', payment_list, mapping_fields_payment, 'paymentId',context={})
        
        for fitnet_payment in payment_list:
            odoo_payment = self.env['account.payment'].search([('fitnet_id', '=', fitnet_payment['paymentId'])])[0]
            if odoo_payment.is_reconciled:
                continue
            payment_line_to_reconcile = False
            for line in odoo_payment.move_id.line_ids:
                if line.account_id.code == '411100':
                    payment_line_to_reconcile = line
        
            odoo_invoice =  self.env['account.move'].search([('fitnet_id', '=', fitnet_payment['inoviceId'])])[0]
            invoice_line_to_reconcile = False
            for line in odoo_invoice.line_ids:
                if line.account_id.code == '411100':
                    invoice_line_to_reconcile = line
            
            if (invoice_line_to_reconcile and payment_line_to_reconcile) :
                if invoice_line_to_reconcile.move_id.state == 'draft' :
                    invoice_line_to_reconcile.move_id.action_post()
                if payment_line_to_reconcile.move_id.state == 'draft' :
                    payment_line_to_reconcile.move_id.action_post()
                (payment_line_to_reconcile + invoice_line_to_reconcile).reconcile()
        """

        #TODO : générer l'adresse de facturation du partner si différente de celle déjà connue (ou MAJ de la fiche partenaire si l'adresse postale est vide
            # attribut billingAdress de l'objet invoice Fitnet
        #TODO : generer le project.milestone et y rattacher la facture (date du jalon = bilingDueDate dans le modèle fitnet)
        #TODO : gérer les factures et avoirs fournisseurs (ie de nos sous-traitants)
            # récupérer les founisseurs : https://tasmane.fitnetmanager.com/FitnetManager/rest/suppliers/1/2
            # récupérer les statuts possibles pour les achats : https://tasmane.fitnetmanager.com/FitnetManager/rest/monitoringPurchases/getAllStatus/1
            # récupérer les achats : https://tasmane.fitnetmanager.com/FitnetManager/rest/monitoringPurchases/1/all/01-2018/06-2050 

           

    def sync_suppliers(self, client):
        _logger.info('--- sync_suppliers')
        suppliers = client.get_api("suppliers/1/1")

        for supplier in suppliers:
            supplier['id_odoo'] = 'supplier_'+str(supplier['supplierId'])
            if supplier['siret']:
                supplier['siret'] = supplier['siret'].replace(' ', '').replace('.', '')
            #elif supplier['siren']:
            #    supplierr['siret'] = supplier['siren'].replace(' ', '').replace('.', '')
            if supplier['vatNumber']:
                supplier['vatNumber'] = supplier['vatNumber'].replace(' ', '').replace('.', '')

            mapping_fields = {
                'name' : {'odoo_field' : 'name'},
                'vatNumber' : {'odoo_field' : 'vat'}, 
                'code' : {'odoo_field' : 'ref'},
                'siret' : {'odoo_field' : 'siret'},

               # 'address_streetNumber' : {'odoo_field' : 'street'},
               # 'address_additionnalAddressInfo' : {'odoo_field' : 'street2'},
               # 'address_additionnalAddressInfo2' : {'odoo_field' : 'street3'},
               # 'address_zipCode' : {'odoo_field' : 'zip'},
               # 'address_city' : {'odoo_field' : 'city'},
               # 'default_invoice_payement_bank_account' : {'odoo_field' : 'default_invoice_payement_bank_account'},
            }
        odoo_model_name = 'res.partner'
        self.create_overide_by_fitnet_values(odoo_model_name, suppliers, mapping_fields, 'id_odoo')


    def sync_supplier_invoices(self, client):
        _logger.info('--- sync_supplier_invoices')
        supplier_invoices = client.get_api("monitoringPurchases/1/all/01-2018/12-2050")

        nature_list = {}
        for supplier_invoice in supplier_invoices:
            if supplier_invoice['natureId'] not in nature_list.keys():
                nature_list[supplier_invoice['natureId']] = {'libelle' : supplier_invoice['nature'], 'count' : 1}
            else :
                nature_list[supplier_invoice['natureId']]['count'] += 1
        _logger.info(len(nature_list))
        _logger.info(nature_list)

        # Fitnet Status of the Purchase: -1 [Canceled], 0 [Planned], 1 [Confirmed], 2 [Invoice received] or 3 [Paid] (Status can only be reached one by one, apart from [Canceled] that can be reached from any status and from [Paid] as well, accounting that an Actual Payment Date is set and the concerned setting is enabled)

        mapping_fields_invoice = {
            'invoiceNumber' : {'odoo_field' : 'name'},
            'odoo_supplierId' : {'odoo_field' : 'partner_id'},
            'paymentConditionsId' : {'odoo_field' : 'invoice_payment_term_id'},
            'date' : {'odoo_field' : 'date'},
            'invoice_date' : {'odoo_field' : 'invoice_date'},
            'dueDate' : {'odoo_field' : 'invoice_date_due'},
            'move_type' : {'odoo_field' : 'move_type', 'selection_mapping' : {'in_invoice' : 'in_invoice', 'in_refund' : 'in_refund'}},
            'ibanId' : {'odoo_field' : 'partner_bank_id'},
            #'referenceInvoiceNumber' : {'odoo_field' : 'invoice_origin'},
            # : {'odoo_field' : 'reversal_move_id'}
            #'odoo_state' : {'odoo_field' : 'state', 'selection_mapping' : {'0' : 'draft', '1' : 'draft', '2':'posted', '3' : 'posted', '-1' : 'cancel'}},
            #'odoo_payment_state' : {'odoo_field' : 'payment_state', 'selection_mapping' : { : 'not_paid', : 'in_payment', : 'paid', : 'partial', : 'reversed', : 'invoicing_legacy'}}
        }
        #TODO : alimenter le partner_bank_id
        mapping_fields_invoice_line = {
            'odoo_purchaseId' : {'odoo_field' : 'move_id'},
            'title' : {'odoo_field' : 'name'},
            'unitPrice' : {'odoo_field' : 'price_unit'},
            'quantity' : {'odoo_field' : 'quantity'},
            'contractId_json' : {'odoo_field' : 'analytic_distribution'},
            #product_id
        }
        mapping_fields_payment = {
            'odoo_supplierId' : {'odoo_field' : 'partner_id'},
            'amount' : {'odoo_field' : 'amount'},
            'date' : {'odoo_field' : 'date'},
            'payment_type' : {'odoo_field' :'payment_type', 'selection_mapping' : {'inbound' : 'inbound', 'outbound' : 'outbound'}},
            #'partner_bank_id' : {'odoo_field' : 'partner_bank_id'},
            #'odoo_state' : {'odoo_field' : 'state', 'selection_mapping' : {'draft' : 'draft', 'posted':'posted', 'cancel' : 'cancel'}},
            'journal_id' : {'odoo_field' : 'journal_id'},
            'partner_type' : {'odoo_field' : 'partner_type',  'selection_mapping' : {'customer' : 'customer', 'supplier' : 'supplier'}},
        }
        invoices_list = []
        invoices_lines_list = []
        payment_list = []

        purchaseId_unicity_ctrl = {}
        for invoice in supplier_invoices:
            fonc_key = invoice['purchaseId']
            if fonc_key not in purchaseId_unicity_ctrl.keys():
                purchaseId_unicity_ctrl[fonc_key] = {'count' : 0, 'invoice_list' : []}
            purchaseId_unicity_ctrl[fonc_key]['count'] += 1
            purchaseId_unicity_ctrl[fonc_key]['invoice_list'].append(invoice)
            
        """
        for pid, val in purchaseId_unicity_ctrl.items():
            if val['count'] > 1:
                _logger.info(pid)
                _logger.info(val['count'])
                _logger.info(val['invoice_list'])
        """

        for invoice in supplier_invoices:
            invoice['odoo_purchaseId'] = 'supplier_' + str(invoice['purchaseId']) #ATTENTION : l'API ne retourne pas un purchaseId unique, il est réutilisé si annulation.
            #Si le purchaseId n'est pas unique, alors la clé fonctionnelle est la concaténation du purchaseId et du orderNumber
            # AVANTAGE : les changements d'orderNumber n'impacteront que les rares avec des purchaseId non nuls => les autres ne seront pas sensisbles au changement de orderNumber
            # INCONVENIENT : on va créer des doublons lors de la synchro juste après avoir créé le premier doublon ==> TODO : exécuter la fonction de néttoyage sur Odoo des éléments supprimés dans Fitnet
            if purchaseId_unicity_ctrl[invoice['purchaseId']]['count'] > 1:
                invoice['odoo_purchaseId'] = 'supplier_' + str(invoice['orderNumber']) + '_' + str(invoice['purchaseId']) 
            invoice.pop('purchaseId')
            if invoice['odoo_purchaseId'] not in ['supplier_682', 'supplier_790']:
                continue
            if invoice['purchaseStatus'] in ['0', '1']:
                continue
            if invoice['natureId'] in ['1']: #sous traitance
                continue
                #TODO pour gérer les natures différentes  créer un article différent par compte comptable différent ou taux de taxe différent
            if invoice['amountBeforeTax'] < 0:
                #_logger.info('avoir fitnet invoiceId=' + str(invoice['odoo_purchaseId']))
                invoice['move_type'] = 'in_refund'
            else :
                invoice['move_type'] = 'in_invoice'
            invoice['odoo_supplierId'] = 'supplier_'+str(invoice['supplierId'])
            invoice['ibanId'] = None
            invoice['invoice_date'] = invoice['date']
            invoices_list.append(invoice)

            
            #if len(invoice['purchaseItems']) != 1 :
            #    _logger.info("Facture fournisseur %s Nombre de lignes de facture différent de 1 : %" % (invoice['invoiceNumber'], str(len(invoice['purchaseItems']))))

            for line in invoice['purchaseItems']:
                line['odoo_purchaseId'] = invoice['odoo_purchaseId']
                line.pop('purchaseId')
                line['odoo_purchaseLineId'] = 'supplier_'+str(line['id'])
                line.pop('id')
                line['unitPrice'] = abs(line['unitPrice']) #ATTENTION : contrairement aux avoirs clients, l'API Fitnet retourne un montant négatif pour les avoirs fournisseurs => il faut donc prendre la valeur absolue
                odoo_analytic_ccount_id_project = self.env['project.project'].search([('fitnet_id', '=', invoice['contractId'])])[0].analytic_account_id.id
                line['contractId_json'] = {str(odoo_analytic_ccount_id_project) : 100.0} 
                line['quantity'] = 1.00
                invoices_lines_list.append(line)
                #if line['vatRate'] != 20.0:
                #    raise ValidationError(_("Taux de TVA != 20%"))

            if invoice['actualPayementDate'] != "" :
                payment = {
                        'supplier_paymentId' : 'payment_purchase_' + str(invoice['odoo_purchaseId']),
                        'purchaseId' : invoice['odoo_purchaseId'],
                        'odoo_supplierId' : invoice['odoo_supplierId'],
                        'amount' : "%.2f" % round(abs(invoice['amountWithTax']),2),
                        'date' : invoice['actualPayementDate'],
                        'proprieteOnDemand' : [],
                        'partner_type' : 'supplier',
                    }
                if invoice['move_type'] == 'in_invoice' : 
                    payment['payment_type'] = 'outbound'
                elif invoice['move_type'] == 'in_refund' :
                    payment['payment_type'] = 'inbound'
                payment['journal_id'] = 99
                #payment['partner_bank_id'] = invoice['ibanId']
                payment_list.append(payment)

        self.create_overide_by_fitnet_values('account.move', invoices_list, mapping_fields_invoice, 'odoo_purchaseId',context={})
        self.create_overide_by_fitnet_values('account.move.line', invoices_lines_list, mapping_fields_invoice_line, 'odoo_purchaseLineId',context={})
        self.create_overide_by_fitnet_values('account.payment', payment_list, mapping_fields_payment, 'supplier_paymentId',context={})
        
        for fitnet_payment in payment_list:
            odoo_payment = self.env['account.payment'].search([('fitnet_id', '=', fitnet_payment['supplier_paymentId'])])[0]
            if odoo_payment.is_reconciled:
                continue
            payment_line_to_reconcile = False
            account_number = '604000'
            for line in odoo_payment.move_id.line_ids:
                if line.account_id.code == account_number: #TODO : le compte dépend de la nature d'achat
                    payment_line_to_reconcile = line
        
            odoo_invoice =  self.env['account.move'].search([('fitnet_id', '=', fitnet_payment['purchaseId'])])[0]
            invoice_line_to_reconcile = False
            for line in odoo_invoice.line_ids:
                if line.account_id.code == account_number:
                    invoice_line_to_reconcile = line
            
            if (invoice_line_to_reconcile and payment_line_to_reconcile) :
                if invoice_line_to_reconcile.move_id.state == 'draft' :
                    invoice_line_to_reconcile.move_id.action_post()
                if payment_line_to_reconcile.move_id.state == 'draft' :
                    payment_line_to_reconcile.move_id.action_post()
                (payment_line_to_reconcile + invoice_line_to_reconcile).reconcile()

        #Montant du BC client : montant projet Berny + somme des factures fournisseurs de natureId 2 = 'Sous-traitance'
            #On ne devrait avoir de telles factures que pour les missions avec sous-traitance paiement tasmane ou Tasmnae+direct

        #Restera à compléter sur Odoo :
            # Si uniquement dispositif Tasmane : rien à faire ?
            # Si cotraitance : le montant du BC hors pilotage Tasmane sur le BC client
            # Si sous-traitance (avec ou sans paiement direct) : la valorisation des parts dispositif Tasmane (sur la fiche projet) et S/T (sur le BC fournisseur)
            # Si paiement direct + Tasmane : le montant du paiement direct (sur le BC client et le BC fournisseur => ligne générée à 0)
            # Si uniquement paiement direct (PAS DE MARKUP ?) : le lien est fait automatiquement par la reprise de données mais devra être vérifié
            # Pour les paiements directs déjà en partie payés => remplir le montant de paimeent direct déjà réalisé sur les lignes des BC fournisseurs et les ref Chorus


    def sync_employees_contracts(self, client):
        _logger.info('--- synch_employees_contracts')
        employee_contracts = client.get_api("employmentContracts")

        for contract in employee_contracts:
            contract['name'] = contract['employeeName'] + " - " + contract['effective_date']
            contract['wage'] = 0.0

            contract['leaving_date_previous_day'] = False
            if contract['leaving_date']:
                if contract['effective_date'] == contract['leaving_date']:
                    contract['leaving_date_previous_day'] = contract['leaving_date']
                else:
                    leaving_date_previous_day = datetime.datetime.strptime(contract['leaving_date'], '%d/%m/%Y').date() - datetime.timedelta(days=1)
                    contract['leaving_date_previous_day'] = leaving_date_previous_day.strftime("%d/%m/%Y")

            if contract['leaving_date']:
                contract['state'] = 'close'
            else :
                contract['state'] = 'open'
            #il n'y a pas de statut de contrat dans l'API Fitnet, donc pas d'équivalent au statut annulé
            #TODO : pour les contrat avec une effective_date dans le futur, mettre un statut = draft

        mapping_fields = {
            'name' : {'odoo_field' : 'name'},
            'employee_id' : {'odoo_field' : 'employee_id'},
            'state' : {'odoo_field' : 'state', 'selection_mapping' : {'open' : 'open', 'close' : 'close'}},
            'effective_date' : {'odoo_field' : 'date_start'},
            'leaving_date_previous_day' : {'odoo_field' : 'date_end'},
            'collaboratorProfileId' : {'odoo_field' : 'job_id'},
            'wage' : {'odoo_field' : 'wage'},
            #contract_type_id
            #qualification
            #positionName
            #coefficientSituationName
            #end_date_of_trial_period
            #nb_days_per_year
            #part_time
            }
        odoo_model_name = 'hr.contract'
        self.create_overide_by_fitnet_values(odoo_model_name, employee_contracts, mapping_fields, 'employment_contract_id')
               
    def sync_employees(self, client):
        _logger.info('--- synch_employees')
        employees = client.get_api("employees/1")
        _logger.info('nb employees ' + str(len(employees)))

        #Intégrer l'id Fitnet aux hr.employee si on peut le trouver via l'email du hr.employee ou bien d'un res_users (et dans ce cas création du hr.employee à la volée)
        for employee in employees:
            odoo_employee = self.env['hr.employee'].search([('fitnet_id','=',employee['employee_id']), ('active', 'in', [True, False])])
            if len(odoo_employee) > 1 :
                _logger.info("Plus d'un hr.employee a cet id fitnet %s" % str(employee['employee_id']))
                continue
            if len(odoo_employee) == 0 :
                _logger.info(employee['name'])
                _logger.info(employee['email'])
                if not employee['email']:
                    _logger.info("Pas d'email sur Fitnet")
                    continue
                #intégrer l'ID Fitnet au hr.employee
                odoo_employee = self.env['hr.employee'].search([('work_email','=',employee['email']), ('fitnet_id', '=', False)])
                if len(odoo_employee) > 1 :
                    _logger.info("Erreur : plusieurs hr.employee on ce work_email : %s" % employee['email'])
                    continue
                if len(odoo_employee) == 0:
                    #créer l'employé Odoo s'il existe un user Odoo qui porte le même identifiant
                    odoo_user = self.env['res.users'].search([('login','=',employee['email']), ('employee_id','=',False)])
                    if len(odoo_user) == 1:
                        odoo_user.action_create_employee()
                        _logger.info("Création de l'employée depuis l'utilsiateur avec le login=%s" % odoo_user.login)
                        odoo_employee = odoo_user.employee_id
                    else :
                        _logger.info("Aucun hr.employee ni res.users Odoo pour FitnetID=%s / Fitnet email=%s" % (employee['employee_id'],employee['email']))
                        continue
                odoo_employee.fitnet_id = employee['employee_id']
                _logger.info("Intégration de l'ID Fitnet pour le hr.employee :  Odoo ID=%s / Odoo name=%s / FitnetID=%s / Fitnet name=%s" % (odoo_employee.id, odoo_employee.name, employee['employee_id'], employee['name']))
        
        #Pour les employee qui existent sur Fitnet mais pas sur Odoo (exemple : anciens tasmaniens) : on crée le hr.employee mais sans res_user associé
            #TODO : créer le res_user associé si la date d'entrée fitnet > date du jour et que date de sortie non défini ou > date du jour
        # ... puis mettre à jour les valeurs des employés Odoo
        mapping_fields = {
            'name' : {'odoo_field' : 'name'},
            'profile_id' : {'odoo_field' : 'job_id'},
            'surname' : {'odoo_field' : 'first_name'},
            'email' : {'odoo_field' : 'work_email'},
            'gender' : {'odoo_field' : 'gender', 'selection_mapping' : {'Male' : 'male', 'Female' : 'female'}},
            #registration_id
            #hiringDate => attribut du hr.contract
            #leavingDate => attribut du hr.contract
            #foreignEmployee
            #address
            #zone_23_key_P_1-S_1 #Champ onDemande pour l'email personnel
            #zone_23_key_P_268-S_1 #Champ onDemande pour le mobile personnel
            }
        odoo_model_name = 'hr.employee'
        self.create_overide_by_fitnet_values(odoo_model_name, employees, mapping_fields, 'employee_id', filters=[('active', 'in', [True, False])])


    def sync_project(self, client):
        _logger.info('--- synch projects')
        projects = client.get_api("projects/1")
        mapping_fields = {
            'title' : {'odoo_field' : 'name'},
            'customer' : {'odoo_field' : 'partner_id'},
            }
        odoo_model_name = 'project.group'
        self.create_overide_by_fitnet_values(odoo_model_name, projects, mapping_fields, 'projectId')



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


        dm_list = self.env['hr.employee'].search([('job_id', 'in', [5, 6, 7, 10])])
        _logger.info(dm_list)
        DMFitnetIDList = []
        for dm in dm_list:
            DMFitnetIDList.append(dm.fitnet_id)
        _logger.info(DMFitnetIDList)

        for obj in fitnet_objects:
            # Transco de la liste déroulante Bon de commmande reçu en un booléen sur Odoo
            if self.get_proprieteOnDemand_by_id(obj, "zone_13_key_P_1-S_1")  == "Reçu":
                obj['is_purchase_order_received'] = True
            else:
                obj['is_purchase_order_received'] = False
        
            # Recherche du res.user Odoo qui correspond au DM de la mission
            comList = []
            for com in obj['affectedCommercialsList']:
                if str(com['employeeId']) in DMFitnetIDList :
                    comList.append(com)
            comList = sorted(comList, key=lambda x: x['employeeId'])

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

        #self.delete_not_found_fitnet_object(odoo_model_name, fitnet_objects, 'contractId')
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
                old_odoo_values, dict_dif = self.prepare_update_from_fitnet_values(odoo_model_name, fitnet_object, mapping_fields, odoo_object)
                if len(dict_dif) > 0:
                    #import copy
                    #old_dict_dif = copy.copy(dict_dif)
                    #dic_old_values = odoo_object.with_context(context).read()[0]
                    #_logger.info("Fitnet object : %s" % str(fitnet_object))
                    _logger.info("Mise à jour de l'objet %s ID= %s (fitnet_id = %s) avec les valeurs de Fitnet %s" % (odoo_model_name, str(odoo_object.id), str(fitnet_id), str(dict_dif)))
                    _logger.info("      > Old odoo values : %s" % str(old_odoo_values))
                    odoo_object.with_context(context).write(dict_dif)
                    #dic_new_values = odoo_object.with_context(context).read()[0]
                    #_logger.info("Changements apportés :")
                    #for field in old_dict_dif.keys() :
                    #    _logger.info("          > %s : %s => %s" %(field, dic_old_values[field], dic_new_values[field]))
            if len(odoo_objects) == 0 :
                old_odoo_values, dic = self.prepare_update_from_fitnet_values(odoo_model_name, fitnet_object, mapping_fields)
                dic['fitnet_id'] = fitnet_id
                _logger.info("Creating Odoo instance of %s object for fitnet %s=%s with values %s" % (odoo_model_name, fitnet_id_fieldname, fitnet_id, str(dic)))
                odoo_object = self.env[odoo_model_name].with_context(context).create(dic)
                _logger.info("Odoo object created, Odoo ID=%s" % (str(odoo_object.id)))

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
            old_odoo_value = {}
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
                            #_logger.info("      Ancienne valeur dans Odoo pour l'attribut %s de l'objet %s (Odoo ID = %s): %s" % (odoo_field_name, odoo_model_name, str(odoo_object['id']), odoo_object[odoo_field_name]))
                            #_logger.info("              > Nouvelle valeur : %s" % odoo_value)
                            old_odoo_value[odoo_field_name] = odoo_object[odoo_field_name]
                            res[odoo_field_name] = odoo_value
                    else :
                            res[odoo_field_name] = odoo_value


                if odoo_field.ttype == "many2one" :
                    if fitnet_value == None : #le champ many2one était valorisé sur Fitnet, mais a été remis à blanc sur Fitnet
                        if odoo_object :
                            if odoo_object[odoo_field_name] :
                                res[odoo_field_name] = False
                                old_odoo_value[odoo_field_name] = odoo_object[odoo_field_name]
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
                                #_logger.info("      Ancienne valeur dans Odoo pour l'attribut MANY TO ONE %s de l'objet %s (Odoo ID = %s): %s" % (odoo_field_name, odoo_model_name, str(odoo_object['id']), odoo_object[odoo_field_name]))
                                #_logger.info("              > Nouvelle valeur : %s" % odoo_value)
                                old_odoo_value[odoo_field_name] = odoo_object[odoo_field_name]
                        else :
                            res[odoo_field_name] = odoo_value

                    if len(target_objects) == 0 :
                        odoo_id = ""
                        if odoo_object :
                            odoo_id = odoo_object['id']
                        _logger.info("Alimentation du champ %s pour l' object Odoo %s (ID ODOO = %s)" % (odoo_field_name, odoo_model_name, str(odoo_id)))
                        _logger.info("      > Erreur - impossible de trouver l'objet lié : aucun objet %s n'a de fitnet_id valorisé à %s" % (odoo_field.relation, fitnet_value))
                        continue
                #écraser la valeur Odoo par la valeur Fitnet si elles sont différentes
                if odoo_value is None:
                    _logger.info("Type %s non géré pour le champ Fitnet %s = %s" % (odoo_field.ttype, fitnet_field_name, fitnet_value))
                    continue

            return old_odoo_value, res

