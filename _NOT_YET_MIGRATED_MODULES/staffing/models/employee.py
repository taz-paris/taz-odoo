from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime, timedelta
import pytz


import logging
_logger = logging.getLogger(__name__)

class staffingEmployee(models.Model):
    _inherit = "hr.employee"
    _order = "first_name, name"

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


    def availability_4_weeks_graph(self):
        pass
    
    
    def last_validated_timesheet_date(self):
        for rec in self:
            timesheets = self.env['account.analytic.line'].search([('employee_id', '=', rec.id),('category', '=', 'project_employee_validated')], order='date desc')
            if len(timesheets)>0 :
                lvt = timesheets[0].date
                rec.last_validated_timesheet_date = lvt
                #monday2weeks = datetime.today() - datetime.timedelta(days = datetime.today().weekday() + 7)
                #if lvt < monday2weeks :
                #    rec.is_last_validated_timesheet = True
                #else : 
                #    rec.is_last_validated_timesheet = False
            else :
                rec.last_validated_timesheet_date = False

    @api.depends('last_validated_timesheet_date')
    def is_late_validated_timesheet(self):
        for rec in self:
                lvt = rec.last_validated_timesheet_date
                if lvt :
                    monday2weeks = datetime.today() - timedelta(days = datetime.today().weekday() + 7)
                    if lvt < monday2weeks.date() :
                        rec.is_late_validated_timesheet = True
                    else :
                        rec.is_late_validated_timesheet = False
                else :
                    rec.is_late_validated_timesheet = False

    def send_email_timesheet_late(self):
        for rec in self:
            if not rec.work_email:
                continue
            body = 'Bonjour</br>Votre dernier pointage date du %s.</br>Merci de compléter votre saisie au plus vite.</br>Cordialement.' % (rec.last_validated_timesheet_date.strftime('%d/%m/%Y'))
            subject = 'Notification de saisie incomplète'
            email_from = self.env['ir.mail_server'].search([('id','=',1)])
            email_to = rec.work_email
            values = {
                'res_id' : rec.id,
                'email_from' : email_from.smtp_user,
                'email_to' : email_to,
                'auto_delete' : False,
                'model' : 'hr.employee',
                'body_html' : body,
                'subject' : subject,
                }

            send_mail = self.env['mail.mail'].sudo().create(values)
            send_mail.send()


    @api.depends('contract_id', 'contract_id.job_id')
    def compute_employee_job_id(self):
        for rec in self:
            rec.job_id = rec.contract_id.job_id

    first_name = fields.Char(string="Prénom")
    staffing_wishes = fields.Html("Souhaits de staffing COD")
    staffing_need_ids = fields.One2many('staffing.need', 'staffed_employee_id', string="Affectations")

    last_validated_timesheet_date = fields.Date("Date du dernier pointage validé", compute=last_validated_timesheet_date)
    is_consultant = fields.Boolean("Est consultant", default="True")
    is_late_validated_timesheet = fields.Boolean("Pointage en retard", compute=is_late_validated_timesheet)
    is_associate = fields.Boolean("Est associé")
    mentee_ids = fields.One2many('hr.employee', 'coach_id', string="Mentees")
    sector_ids = fields.Many2many('res.partner.industry', string="Compte (ex BD)")
    annual_evaluator_id = fields.Many2one('res.partner', string="En charge de l'EA")
    cv_link = fields.Char('Lien CV')
    vcard_link = fields.Char('Lien VCard') #TODO : générer la VCARD depuis les données Odoo
    job_id = fields.Many2one(check_company=False, store=True, compute='compute_employee_job_id')
    rel_is_project_director = fields.Boolean(related="job_id.is_project_director", store=True)

    #most_recent_contract = fields.Many2one('hr.contract', 'employee_id', string="Contract le plus récent (ou à venir)", compute=most_recent_contract)

    def _get_daily_cost_today(self):
        t = datetime.today().date() 
        for rec in self:
            rec.daily_cost_today, cost_line = rec._get_daily_cost(t)
    daily_cost_today = fields.Float("CJM actuel", compute=_get_daily_cost_today)

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
            if contract.date_start <= date :
                if contract.date_end and contract.date_end < date:
                    continue
                res = contract
        return res

    def _get_work_location_id(self, date):
        contract = self._get_contract(date)
        if contract :
            return contract.work_location_id
        return False

    def _get_job_id(self, date):
        contract = self._get_contract(date)
        if contract :
            return contract.job_id
        #_logger.info('Pas de contrat pour ce consultant à cette date')
        return False

    def _get_daily_cost(self, date):
        contract = self._get_contract(date)
        cost = False
        cost_line = False
        if contract :
            cost, cost_line = contract._get_daily_cost(date)
        return cost, cost_line


    def number_days_available_period(self, date_start, date_end):
        #_logger.info('number_days_available_period %s' % self.name)
        self.ensure_one()
        if date_start > date_end :
            raise ValidationError(_("Start date should be <= end date"))
        res = self.number_work_days_period(date_start, date_end) - self.number_not_available_period(date_start, date_end)
        #_logger.info('Availability : %s' % str(res))
        return res

    def number_not_available_period(self, date_start, date_end):
        #_logger.info("number_not_available_period")
        self.ensure_one()
        if date_start > date_end :
            raise ValidationError(_("Start date should be <= end date"))
        dic = [('employee_id', '=', self.id)]
        pivot_date = datetime.today()
        lines = self.env['account.analytic.line'].get_timesheet_grouped(pivot_date, date_start=date_start, date_end=date_end, filters=dic)['aggreation_by_project_type']
        c = lines['mission']['project_employee_validated']['sum_period_unit_amount'] + lines['mission']['project_forecast']['sum_period_unit_amount'] + lines['holidays']['other']['sum_period_unit_amount']
        #_logger.info("       > %s" % str(c))
        return c

    def number_work_days_period(self, date_start, date_end):
        #_logger.info('numbers_work_days_period %s du %s au %s' % (self.name, str(date_start), str(date_end)))
        self.ensure_one()
        count = len(self.list_work_days_period(date_start, date_end))
        return count

    def list_work_days_period(self, date_start, date_end):
        self.ensure_one()
        list_work_days_period_common = self.list_work_days_period_common(date_start, date_end)
        res = []
        for day in list_work_days_period_common :
            if self._get_contract(day) :
                res.append(day)
        return res

    def list_work_days_period_common(self, date_start, date_end):
        res = []
        if date_start > date_end :
            raise ValidationError(_("Start date should be <= end date"))
        date = date_start
        while (date != False and date <= date_end):
            #user_tz = self.env.user.tz or str(pytz.utc)
            user_tz = 'Europe/Paris'
            local = pytz.timezone(user_tz)
            search_public_holiday_begin = datetime(date.year, date.month, date.day, 0, 0, 0)
            search_public_holiday_begin = local.localize(search_public_holiday_begin, is_dst=None)
            search_public_holiday_begin = search_public_holiday_begin.astimezone()

            search_public_holiday_end = datetime(date.year, date.month, date.day, 23, 59, 59)
            search_public_holiday_end = local.localize(search_public_holiday_end, is_dst=None)
            search_public_holiday_end = search_public_holiday_end.astimezone()

            public_holidays = self.env['resource.calendar.leaves'].search([('resource_id', '=', False), ('time_type', '=', 'leave'), ('date_from', '>=', search_public_holiday_begin), ('date_to', '<=', search_public_holiday_end)])
            #_logger.info('Date begin = %s / date end = %s / Public holidays : %s' % (str(search_public_holiday_begin), str(search_public_holiday_end),  str(public_holidays.read())))
            if len(public_holidays) ==  0:
                if date.isoweekday() not in [6, 7]:
                    res.append(date)
            date = date + timedelta(days = 1) #TODO : ajouter 24h au lieu d'un jour => impact lorsque lors du changement d'heure ? (garder la même heure en passant de GMT +2 à +1 ... ou bien changer d'heure en gardant le même offste ce qui reveint au même pour les comparaisons)
        #_logger.info("       > %s" % str(len(res)))
        #_logger.info("       > %s" % res)
        return res

    def open_employee_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('employee_id', '=', self.id)])
        lines = timesheets_data['aggreation_by_project_type']

        analytic_lines_list_ids = []
        for aggregation in lines.values() :
            for category in aggregation.values() :
                for timesheet in category['timesheet_ids']:
                    analytic_lines_list_ids.append(timesheet.id)

        view_id = self.env.ref("staffing.view_employee_pivot")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage',
                'res_model': 'account.analytic.line',
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', analytic_lines_list_ids)],
                'context': {'search_default_history_3months' : 1},
                'target': 'current',
            }

class staffingUsers(models.Model):
    _inherit = "res.users"

    def _get_employee_fields_to_sync(self):
        res = super()._get_employee_fields_to_sync()
        res.append('first_name')
        return res
