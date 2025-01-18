from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
import pytz


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    current_leave_state = fields.Selection(selection_add=[('canceled', 'Annulée')])

class staffingLeave(models.Model):
    _inherit = 'hr.leave'

    request_date_to_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period End", default='pm')

    #TODO : contrôler que si date_from = date_to on ne peut pas avoir request_date_from_period=pm ET request_date_to_period==am

    state = fields.Selection(selection_add=[('canceled', 'Annulée')])
        #TODO : le coeur Odoo gère l'annulation avec un booléen active et non pas un statut
            #eave_sudo.with_context(from_cancel_wizard=True).active = False
            #https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_holidays/models/hr_leave.py#L1359


    def write(self_list, vals):
        old_values = {}
        for self in self_list :
            old_values[self.id] = {'date_from' : self.date_from, 'date_to' : self.date_to}

        res = super().write(vals)

        for self in self_list :
            _logger.info(" write hr leave %s" % str(vals))
            old_state = self.state
            if old_state == "validate":
                #TODO : avec cette fonction on met bien à jour les timesheet, mais on ne corrige pas les 'resource.calendar.leaves' associés au congés
                if any(x in ['employee_id', 'holiday_status_id', 'request_date_from', 'request_date_to', 'date_from', 'date_to', 'number_of_days', 'request_date_from_period', 'request_date_to_period', 'state'] for x in vals.keys()):
                    _logger.info("Changement sur le congés conduisant à supprimer et recréer les timesheets liées. %s" % str(vals))
                    holidays = self.filtered(
                        lambda l: l.holiday_type == 'employee' and
                        l.holiday_status_id.timesheet_project_id and
                        l.holiday_status_id.timesheet_task_id and
                        l.holiday_status_id.timesheet_project_id.sudo().company_id == (l.holiday_status_id.company_id or self.env.company))

                    # Unlink previous timesheets to avoid doublon
                    _logger.info("====== Change on hr.leave : Unlink previous timesheets to avoid doublon")
                    _logger.info(holidays)
                    _logger.info(holidays.sudo().timesheet_ids)

                    old_timesheets = holidays.sudo().timesheet_ids
                    if old_timesheets:
                        old_timesheets.holiday_id = False
                        _logger.info("PREPARNG old timesheet to be unlinked %s" % str(old_timesheets.ids))
                        old_timesheets.unlink()
                        _logger.info("old timesheet unlinked %s" % str(old_timesheets.ids))

                    # create the timesheet on the vacation project
                    holidays._timesheet_create_lines()

                    # update timesheets of all overlapped leaves
                    overlapped_leaves =  self.env['hr.leave'].search([
                                                ('id', '!=', self.id),
                                                ('employee_id', '=', self.employee_id.id),
                                                ('state', '=', "validate"),
                                                ('date_from', '<=', max(old_values[self.id]['date_to'], self.date_to)),
                                                ('date_to', '>=', min(old_values[self.id]['date_from'], self.date_from)),
                                                ], order="request_date_from asc")
                    for ol in overlapped_leaves :
                        _logger.info(self.env.context.get('overlapped_already_updated', ''))
                        overlapped_already_updated_str = self.env.context.get('overlapped_already_updated', '')
                        if not(overlapped_already_updated_str):
                            overlapped_already_updated_str = ""
                        if str(ol.id) not in overlapped_already_updated_str.split(',') :
                            ol.with_context(overlapped_already_updated=overlapped_already_updated_str+str(self.id)+',').number_of_days = ol.number_of_days 

        return res


    def unlink(self):
        self_id = self.id
        overlapped_leaves =  self.env['hr.leave'].search([
                                    ('id', '!=', self.id),
                                    ('employee_id', '=', self.employee_id.id),
                                    ('state', '=', "validate"),
                                    ('date_from', '<=', self.date_to),
                                    ('date_to', '>=', self.date_from),
                                    ], order="request_date_from asc")

        res = super().unlink()

        for ol in overlapped_leaves :
            _logger.info(self.env.context.get('overlapped_already_updated', []))
            current_context = self.env.context.get('overlapped_already_updated', []) or []
            if ol.id not in current_context :
                ol.with_context(overlapped_already_updated=current_context.append(self.id)).number_of_days = ol.number_of_days 

        return res


    def _get_leaves_on_public_holiday(self):
        # Lors de la clôture d'un contrat de travail, les congés postérieurs à la date de fin ne sont pas supprimés sur Napta (soit ils ne sont pas supprimés de Lucca,
        # soit le connecteur Napta oublie d'interroger Lucca post cloture du contrat).
        # Or la durée est calculée à 0 jours dans le module Napta
        # On surchage cette fonction pour ne pas remonter ces congés à la fonction appelante (action_validate), ce qui bloque la création/mise à jour du congés.
        super()._get_leaves_on_public_holiday()
        return False

    #override to deal with uom in days and request_date_to_period
    #odoo/addons/project_timesheet_holidays/models/hr_holidays.py 
    def _timesheet_create_lines(self):
        vals_list = []
        for leave in self:
            if not leave.employee_id:
                continue

            encoding_uom_id = self.env.company.timesheet_encode_uom_id
            if encoding_uom_id == self.env.ref("uom.product_uom_hour"):
                return super()._timesheet_create_lines()
                #for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                #    vals_list.append(leave._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count))
            if encoding_uom_id == self.env.ref("uom.product_uom_day"):

                leave_timesheets_by_day, list_work_days = leave.get_leave_timesheets_by_day()
                index = 0
                for str_date, day_dic in leave_timesheets_by_day.items() :
                    if day_dic['selected_timesheets_unit_amount_sum'] < day_dic['target_unit_amount']:
                        unit_amount_to_create = day_dic['target_unit_amount'] - day_dic['selected_timesheets_unit_amount_sum']
                        vals_list.append(leave._timesheet_prepare_line_values(index, list_work_days, day_dic['date'], unit_amount_to_create))
                        index += 1

            else : 
                raise ValidationError(_("Company timesheet encoding uom should be either Hours or Days."))

        return self.env['account.analytic.line'].sudo().create(vals_list)


    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count):
        # surchargé pour mieux gérer le multi-company. Napta stockera tous les congés sur le même type, hors le standard Odoo se sert du type de congés pour déterminer le projet et la tache à associer aux analytic.lines créées à la validation du congés.
        # cette surcharge force à utiliser le projet/tache de congés défini dans la configuration générale de l'entreprise. Il ne sera plus possible d'associer des congés à des tâches différentes suivante le type de congés utilisé. En revanche les analytic.line seront rattachés à la bonne entreprise
        self.ensure_one()
        res = super()._timesheet_prepare_line_values(index, work_hours_data, day_date, work_hours_count)
        res['project_id'] = self.employee_company_id.internal_project_id.id
        res['task_id'] = self.employee_company_id.leave_timesheet_task_id.id
        res['account_id'] = self.employee_company_id.internal_project_id.analytic_account_id.id
        res['company_id'] = self.employee_company_id.id
        return res


    def get_leave_timesheets_by_day(self):
        #_logger.info('------ get_leave_timesheets_by_day')
        self.ensure_one()
        leave = self

        res = {}

        user_tz = self.env.user.tz or str(pytz.utc)
        local = pytz.timezone(user_tz)
        date_start = leave.date_from.astimezone(local).date() #Ne garder que date sinon, pour le congés de Gaëlle avant le changement d'heure d'octobre on téiat en GMT+2... et en janvier en GMT+1 et donc on avait toujours le 25/01/2023 car ajouter un jour à GMT+2 restait e GMT+2 même si on passait le 31/10
        date_end = leave.date_to.astimezone(local).date()
        #_logger.info(leave.date_from)
        #_logger.info(leave.request_date_from)
        #_logger.info(date_start)
        #_logger.info(leave.date_to)
        #_logger.info(leave.request_date_to)
        #_logger.info(date_end)

        list_work_days = leave.employee_id.list_work_days_period(date_start, date_end)

        #_logger.info(list_work_days)
        #_logger.info('===============================')

        target_date = date_start
        while (target_date <= date_end):
            dic = {
                    'date' : target_date,
                    'target_unit_amount' : 0.0,
                    'selected_timesheets_unit_amount_sum' : 0.0,
                    'selected_timesheet_list' : [],
                  }
            timesheets = self.env['account.analytic.line'].search([('holiday_id', '!=', False), ('employee_id', '=', leave.employee_id.id), ('date', '=', target_date)])

            if (target_date == leave.request_date_from and leave.request_date_from_period == "pm"):
                dic['target_unit_amount'] = 0.5
                for t in timesheets:
                    if target_date == t.holiday_id.request_date_to and t.holiday_id.request_date_to_period == "am":
                        pass
                    else :
                        dic['selected_timesheets_unit_amount_sum'] += min(t.unit_amount, 0.5)
                        dic['selected_timesheet_list'].append((t, min(t.unit_amount, 0.5)))
            elif (target_date == leave.request_date_to and leave.request_date_to_period == "am"):
                dic['target_unit_amount'] = 0.5
                for t in timesheets:
                    if target_date == t.holiday_id.request_date_from and t.holiday_id.request_date_from_period == "pm":
                        pass
                    else :
                        dic['selected_timesheets_unit_amount_sum'] += min(t.unit_amount, 0.5)
                        dic['selected_timesheet_list'].append((t, min(t.unit_amount, 0.5)))
            else :
                dic['target_unit_amount'] = 1
                for t in timesheets:
                    dic['selected_timesheets_unit_amount_sum'] += t.unit_amount
                    dic['selected_timesheet_list'].append((t, t.unit_amount))

            if target_date not in list_work_days :
                dic['target_unit_amount'] = 0.0

            res[str(target_date)] = dic
            #_logger.info(target_date)
            #_logger.info(dic)
            #for t in dic['selected_timesheet_list']:
            #    _logger.info("      > %s jours retenus pour la timesheet %s" % (str(t[1]), t[0].read(['date', 'unit_amount', 'holiday_id'])))

            target_date = target_date + timedelta(days=1)

        return res, list_work_days

