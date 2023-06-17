from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class timesheetNavigator(models.TransientModel):
    _name = 'timesheet.navigator'
    _description = "Technical object for storing navigation session data."

    user_id = fields.Many2one('res.users', string="Who looks") 
    employee_id = fields.Many2one('hr.employee', string="Consultant")
    begin_date = fields.Date("Semaine du")

    def open_timesheet_navigator(self):
        navigators = self.env['timesheet.navigator'].search([('user_id', '=', self.env.user.id)])
        if len(navigators) == 1:
            rec = navigators[0]
        else :
            d = datetime.today()
            new_current_monday = d - timedelta(days=d.weekday())
            new_current_monday = new_current_monday.date()
            employ = self.env.user.employee_id
            if employ :
                rec = self.env['timesheet.navigator'].create({'user_id' : self.env.user.id, 'begin_date' : new_current_monday, 'employee_id': employ.id})
        return {                
                'type': 'ir.actions.act_window',
                'name': 'Sélection de la semaine et du consultant',
                'res_model': 'timesheet.navigator',
                'res_id': rec.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

    def validate(self):
        return self.env['project.project'].open_timesheet_navigate_weeks('no-change', target='main')


class staffingProject(models.Model):
    _inherit = "project.project"
    _order = "number desc"

    def open_project_pivot_timesheets(self):
        date = datetime.today()
        rec_id = []

        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids']

        for i in rec_ids:
            rec_id.append(i.id)

        pivot_view_id = self.env.ref("staffing.view_project_pivot")
        tree_view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot,tree',
                'view_id': [pivot_view_id.id, tree_view_id.id],
                'domain' : [('id', 'in', rec_id)],
                'context': {},
                'target': 'current',
            }


    def open_forecast_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=date+timedelta(days=-21), date_end=date+timedelta(days=90), filters=[])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids'] + timesheets_data['holiday_timesheet_ids']

        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)

        view_id = self.env.ref("staffing.view_forecast_pivot")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Forecast',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', rec_id)],
                'context': {'pivot_measures': ['unit_amount']},
                'target': 'current',
            }





    def open_timesheet_navigate_weeks(self, sens, target='current'):
        _logger.info('--open_timesheet_navigate_weeks')
        view_id = self.env.ref("staffing.view_timesheets_tree")
        #Impossible to send context to a server action from a menuItem, so we use a dédicated transient model
        # TODO : LIMITS : if the user has 2 web browser tabs opened, the navigation will have conflicts 
        navigators = self.env['timesheet.navigator'].search([('user_id', '=', self.env.user.id)])
        if len(navigators) == 1:
            navigator = navigators[0]
            bd = navigator.begin_date 
            timesheet_current_monday = bd - timedelta(days=bd.weekday())
            if sens == 'next':
                new_current_monday = timesheet_current_monday + timedelta(days=7)
            elif sens == 'previous' :
                new_current_monday = timesheet_current_monday - timedelta(days=7)
            elif sens == 'no-change' :
                new_current_monday = timesheet_current_monday
            employ = navigator.employee_id
            navigator.begin_date = new_current_monday
        else :
            d = datetime.today()
            new_current_monday = d - timedelta(days=d.weekday())
            new_current_monday = new_current_monday.date()
            employ = self.env.user.employee_id
            if employ :
                self.env['timesheet.navigator'].create({'user_id' : self.env.user.id, 'begin_date' : new_current_monday, 'employee_id': employ.id})

        sunday = new_current_monday + timedelta(days=6)

        #TODO : créer à la volée les lignes de prévisionel/pointage manquante (pour tous les staffing qui ont une date début < sunday et une date de fin > monday)
            # ça permettra d'être ceinture et bretelle, notamment pour les lignes de projets interne, formation etc.

        #TODO : si employ == False : ouvrir le wizzard de sélection de l'emplpoyee/date
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=new_current_monday, date_end=sunday, filters=[('employee_id', '=', employ.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids'] + timesheets_data['holiday_timesheet_ids']
        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)
        domain = [('date', '>=', new_current_monday), ('date', '<=', sunday), ('id', 'in', rec_id)]

        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage semaine du %s au %s de %s %s ' % (new_current_monday.strftime('%d/%m/%Y'), str(sunday.strftime('%d/%m/%Y')), employ.first_name or ' ', employ.name or ''),
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'domain' : domain,
                'target': target,
                'context' : {'employee_id' : employ.id},
            }

    def margin_landing_now(self):
        for rec in self :
            negative_total_costs, margin_landing_rate, margin_text = rec.margin_landing_date(datetime.today())
            rec.margin_landing = margin_landing_rate
            rec.margin_text = margin_text

    def margin_landing_date(self, date):
        if not self.order_amount or self.order_amount == 0.0:
            return 0.0, 0.0, ""
       
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        _logger.info(timesheets_data)
        timesheet_total_amount = timesheets_data['validated_timesheet_amount'] + timesheets_data['previsional_timesheet_amount']

        #partner_id = fields.Many2one(required=True, ondelete="restrict")
        negative_total_costs = timesheet_total_amount
        date = fields.Date(string="Date de fin")

        margin_landing_rate = (self.order_amount + negative_total_costs) / self.order_amount * 100
        margin_text = "Projection à terminaison en date du %(monday_pivot_date)s :\n    - %(validated_timesheet_unit_amount).2f jours pointés (%(validated_timesheet_amount).2f €)\n    - %(previsional_timesheet_unit_amount).2f jours prévisionnels (%(previsional_timesheet_amount).2f €)" % timesheets_data
        return negative_total_costs, margin_landing_rate, margin_text

   
    favorite_user_ids = fields.Many2many(string="Intéressés par ce projet")

    margin_landing = fields.Float('Marge à terminaison (%)', compute=margin_landing_now)
    margin_text = fields.Text('Détail de la marge', compute=margin_landing_now)

    staffing_need_ids = fields.One2many('staffing.need', 'project_id')


    @api.depends('project_director_employee_id', 'staffing_need_ids.staffed_employee_id', 'staffing_need_ids.project_id')
    def _compute_user_enrolled_ids(self):
        for rec in self:
            user_enrolled_ids = []
            if rec.user_id :
                user_enrolled_ids.append(rec.user_id.id)
            for need in rec.staffing_need_ids :
                if need.staffed_employee_id.user_id.id :
                    user_enrolled_ids.append(need.staffed_employee_id.user_id.id)
            rec.user_enrolled_ids = [(6, 0, user_enrolled_ids)]

