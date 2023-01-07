from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

from warnings import filterwarnings
filterwarnings(action='ignore', category=DeprecationWarning, message='`np.bool8` is a deprecated alias for `np.bool_`.')
from bokeh.plotting import figure
from bokeh.embed import components
import json

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

    def availability_4_weeks(self):
        d = datetime.now()
        monday =  d - timedelta(days=d.weekday())
        end = monday + timedelta(days=(4*7)-1)

        for rec in self:
            res = rec.number_days_available_period(monday, end) / rec.number_work_days_period(monday, end) * 100
            rec.availability_4_weeks = res

    def availability_4_weeks_graph(self):
        pass
        """    
        for rec in self:
            # Design your bokeh figure:
            fruits = ['Apples', 'Pears', 'Nectarines', 'Plums', 'Grapes', 'Strawberries']
            years = ["2015", "2016", "2017"]

            data = {'fruits' : fruits,
                    '2015'   : [2, 1, 4, 3, 2, 4],
                    '2016'   : [5, 3, 4, 2, 4, 6],
                    '2017'   : [3, 2, 4, 4, 5, 3]}

            p = figure(x_range=fruits, height=250, title="Fruit Counts by Year", toolbar_location=None, tools="hover", tooltips="$name @fruits: @$name")

            p.vbar_stack(years, x='fruits', width=0.9, source=data,
                         legend_label=years)

            p.y_range.start = 0
            p.x_range.range_padding = 0.1
            p.xgrid.grid_line_color = None
            p.axis.minor_tick_line_color = None
            p.outline_line_color = None
            p.legend.location = "top_left"
            p.legend.orientation = "horizontal"
            # fill the record field with both markup and the script of a chart.
            script, div = components(p, wrap_script=False)
            rec.availability_4_weeks_graph = json.dumps({"div": div, "script": script})
        """
    
    
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

    first_name = fields.Char(string="Prénom")
    staffing_wishes = fields.Html("Souhaits de staffing COD")
    staffing_need_ids = fields.One2many('staffing.need', 'staffed_employee_id', string="Affectations")
    availability_4_weeks = fields.Float("% dispo S+4", help="%age de dispo entre le lundi de cette semaine et celui 28 jours après)", compute=availability_4_weeks)
    availability_4_weeks_graph = fields.Char("Graph dispo S+4", compute=availability_4_weeks_graph)
    last_validated_timesheet_date = fields.Date("Date du dernier pointage validé", compute=last_validated_timesheet_date)
    is_late_validated_timesheet = fields.Boolean("Pointage en retard", compute=is_late_validated_timesheet)

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
        #_logger.info('number_days_available_period %s' % self.name)
        if date_start > date_end :
            raise ValidationError(_("Start date should be <= end date"))
        res = self.number_work_days_period(date_start, date_end) - self.number_not_available_period(date_start, date_end)
        #_logger.info('Availability : %s' % str(res))
        return res

    def number_not_available_period(self, date_start, date_end):
        #_logger.info("number_not_available_period")
        dic = [('employee_id', '=', self.id)]
        pivot_date = datetime.today()
        lines = self.env['account.analytic.line'].get_timesheet_grouped(pivot_date, date_start=date_start, date_end=date_end, filters=dic)
        c = lines['validated_timesheet_unit_amount'] + lines['previsional_timesheet_unit_amount'] + lines['holiday_timesheet_unit_amount']
        #_logger.info("       > %s" % str(c))
        return c
        """
        #_logger.info('numbers_not_available_period %s du %s au %s' % (self.name, str(date_start), str(date_end)))
        count = 0.0
        timesheets = self.env['account.analytic.line'].search([('date', '>=', date_start), ('date', '<', date_end), ('employee_id', '=', self.id), ('category', '!=', 'project_draft')])
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
        _logger.info("       > %s" % str(count))
        return count
        """

    def number_work_days_period(self, date_start, date_end):
        #_logger.info('numbers_work_days_period %s du %s au %s' % (self.name, str(date_start), str(date_end)))
        count = 0.0
        date = date_start
        while (date <= date_end):
            public_holidays = self.env['resource.calendar.leaves'].search_count([('resource_id', '=', False), ('date_from', '>=', date), ('date_to', '<=', date)])
            if public_holidays ==  0:
                if date.strftime('%A') not in ['Saturday', 'Sunday']:
                    count +=1.0
            date = date + timedelta(days = 1)
        #_logger.info("       > %s" % str(count))
        return count

    def open_employee_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('employee_id', '=', self.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids'] + timesheets_data['holiday_timesheet_ids']
        #TODO : il peut y avoir un recouvrement entre des congés et du prévisionnel...

        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)

        view_id = self.env.ref("staffing.view_employee_pivot")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage',
                'res_model': 'account.analytic.line',
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', rec_id)],
                'context': {'search_default_history_3months' : 1},
                #'res_id': rec_id,
                #'views': [(view_id.id,'pivot'), (self.env.ref('staffing.view_project_pivot_search').id, 'search')],
                #'search_view_id' : self.env.ref('staffing.view_project_pivot_search').id,
                #'filter' : [('date', '>' , datetime.today()-timedelta(days=91))],
                'target': 'current',
            }

class staffingUsers(models.Model):
    _inherit = "res.users"

    def _get_employee_fields_to_sync(self):
        res = super()._get_employee_fields_to_sync()
        res.append('first_name')
        return res
