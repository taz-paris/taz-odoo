from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


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
                'view_mode': 'pivot,list',
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

