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

    def write(self, vals):
        res = super().write(vals)
        for rec in self :
            #Quand la valeur de l'attribut staffing_aggregation change, tous les aggrégats liées aux timesheets de ce projet doivent être recalculés
            #   la mise à jour du champ related stored rel_project_staffing_aggregation de l'objet account.analytic.line se fait par SQL et ne trigger par la fonction write de l'objet account.analytic.line
            #   cette surcharge de write de project.project
            if "staffing_aggregation" in vals.keys():
                analytic_lines = self.env['account.analytic.line'].search([('project_id', '=', rec.id)])
                analytic_lines.create_update_timesheet_report()
        return res

    def open_project_pivot_timesheets(self):
        date = datetime.today()
        rec_id = []

        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        lines = timesheets_data['aggreation_by_project_type']

        analytic_lines_list_ids = []
        for aggregation in lines.values() :
            for category in aggregation.values() :
                for timesheet in category['timesheet_ids']:
                    analytic_lines_list_ids.append(timesheet.id)


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
                'domain' : [('id', 'in', analytic_lines_list_ids)],
                'context': {},
                'target': 'current',
            }


    def open_forecast_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=(date+timedelta(days=-21)).date(), date_end=(date+timedelta(days=90)).date(), filters=[])
        lines = timesheets_data['aggreation_by_project_type']

        analytic_lines_list_ids = []
        for aggregation in lines.values() :
            for category in aggregation.values() :
                for timesheet in category['timesheet_ids']:
                    analytic_lines_list_ids.append(timesheet.id)

        view_id = self.env.ref("staffing.view_forecast_pivot")
        _logger.info('========================== OKKKKKKK')
        return {
                'type': 'ir.actions.act_window',
                'name': 'Forecast',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', analytic_lines_list_ids)],
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
        lines = timesheets_data['aggreation_by_project_type']

        analytic_lines_list_ids = []
        for aggregation in lines.values() :
            for category in aggregation.values() :
                for timesheet in category['timesheet_ids']:
                    analytic_lines_list_ids.append(timesheet.id)

        domain = [('date', '>=', new_current_monday), ('date', '<=', sunday), ('id', 'in', analytic_lines_list_ids)]

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

    def default_project_director_employee_id(self):
        res = self.env.user.employee_id
        if res and not(res.rel_is_project_director):
            return False
        else :
            return res
   
    favorite_user_ids = fields.Many2many(string="Intéressés par ce projet")

    staffing_need_ids = fields.One2many('staffing.need', 'project_id')
    project_director_employee_id = fields.Many2one(domain="[('rel_is_project_director', '=', True)]", default=default_project_director_employee_id)
    project_manager = fields.Many2one(default=default_project_director_employee_id, required=False) #Si required=True ça bloque la création de nouvelle company
    staffing_aggregation = fields.Selection([
                                    ('mission', 'Mission'),
                                    ('training', 'Formation (activité interne)'),
                                    ('sales', 'Avant-vente/commerce (activité interne)'),
                                    ('other_internal', 'Autre activité interne'),
                                    ('holidays', 'Congés'),
                                    ('unavailability', 'Indisponibilité (réduit le nombre de jours ouvrés)'),
                                ], string='Agrégat de staffing', default='mission', tracking=True)


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

