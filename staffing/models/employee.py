from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class staffingEmployee(models.Model):
    _inherit = "hr.employee"

    def _sync_user(self, user, employee_has_image=False):
        vals  = super()._sync_user(user, employee_has_image) 
        if user.first_name :
            vals['first_name'] = user.first_name
        if user.partner_id:
            vals['work_contact_id'] = user.partner_id.id

        if not 'work_email' in vals.keys():
            if '@' in user.login:
                vals['work_email'] = user.login
        return vals


    def action_create_user(self):
        vals = super().action_create_user()
        if self.first_name:
            vals['context']['default_first_name'] = self.first_name
        if self.work_contact_id:
            vals['context']['default_partner_id'] = self.work_contact_id
        return vals


    first_name = fields.Char(string="Prénom")
    staffing_wishes = fields.Html("Souhaits de staffing COD")

    def name_get(self):
         res = []
         for rec in self:                       
            res.append((rec.id, "%s %s" % (rec.first_name or "", rec.name or "")))
         return res                             
    
    @api.model                              
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []          
        recs = self.browse()    
        if not recs:                    
            recs = self.search(['|', ('first_name', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()     

    def _get_contract(self, date):
        res = False
        for contract in self.contract_ids:
            if contract.date_start <= date and contract.state =='open':
                if contract.date_end and contract.date_end < date:
                    continue
                res = contract
        return res

    def _get_job_id(self, date):
        contract = self._get_contract(date)
        if contract :
            return contract.job_id
        return False

    def _get_daily_cost(self, date):
        job_id = self._get_job_id(date)
        if job_id :
            return job_id._get_daily_cost(date)
        else :  
            return False

    def number_days_available_period(self, date_start, date_end):
        _logger.info('number_days_available_period %s' % self.name)
        if date_start > date_end :
            raise ValidationError(_("Start date should be <= end date"))
        res = self.number_work_days_period(date_start, date_end) - self.number_not_available_period(date_start, date_end)
        _logger.info('Availability : %s' % str(res))
        return res

    def number_not_available_period(self, date_start, date_end):
        #_logger.info('numbers_not_available_period %s du %s au %s' % (self.name, str(date_start), str(date_end)))
        count = 0.0
        timesheets = self.env['account.analytic.line'].search([('date', '>=', date_start), ('date', '<=', date_end), ('employee_id', '=', self.id), ('category', '!=', 'project_draft')])
        for timesheet in timesheets:
            if timesheet.encoding_uom_id == self.env.ref("uom.product_uom_day"):
                #_logger.info("%s du %s categ=%s nb_jours=%s" % (timesheet.name, timesheet.date, timesheet.category, timesheet.unit_amount))
                if timesheet.category == 'project_forecast':
                    #Exclure les prévisionnels si au moins un pointage validé ou un congés existe sur la semaine
                    project_employee_validated = False
                    d = timesheet.date
                    monday =  d - timedelta(days=d.weekday())
                    sunday = monday + timedelta(days=6)
                    #_logger.info("Date : %s => Semaine du lundi %s au dimanche %s" % (str(d), str(monday), str(sunday)))
                    for t in timesheets:
                        if t.date >= monday and t.date <= sunday and t.category != 'project_forecast': #si vacances ou pointage validé sur cette semaine, on exclut
                            project_employee_validated = True
                            #_logger.info('          ==> Exclue')
                    if not project_employee_validated :
                        count += timesheet.unit_amount
                else : 
                    count += timesheet.unit_amount
        #_logger.info("       > %s" % str(count))
        return count

    def number_work_days_period(self, date_start, date_end):
        #_logger.info('numbers_work_days_period %s du %s au %s' % (self.name, str(date_start), str(date_end)))
        count = 0.0
        date = date_start
        while (date <= date_end):
            public_holidays = self.env['resource.calendar.leaves'].search_count([('resource_id', '=', False), ('date_from', '>=', date_start), ('date_to', '<=', date_end)])
            if public_holidays ==  0:
                if date.strftime('%A') not in ['Saturday', 'Sunday']:
                    count +=1.0
            date = date + timedelta(days = 1)
        #_logger.info("       > %s" % str(count))
        return count


class staffingUsers(models.Model):
    _inherit = "res.users"

    def _get_employee_fields_to_sync(self):
        res = super()._get_employee_fields_to_sync()
        res.append('first_name')
        return res
