from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _
import datetime
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

    
class wizardAccountingClosingMassCreation(models.TransientModel):
    _name = 'wizard_accounting_closing_mass_creation'
    _description = "wizard_accounting_closing_mass_creation"
    _check_company_auto = True


    @api.onchange('date', 'company_id')
    def _onchange_date(self):
        self.project_ids = False
        p = self.env['project.project'].search([('is_generate_project_accounting_closing', '=', True), ('company_id', '=', self.company_id.id), '|', ('has_provision_running', '=', True), ('stage_id.state', 'in', ['before_launch', 'launched'])])
        self.project_ids = p.ids

        
        analytic_lines, begin_period = self.get_warning_analytic_lines()
        employee_name_list = []
        for line in analytic_lines:
            employee_name_list.append("%s %s" % (line.employee_id.first_name, line.employee_id.name))

        if len(employee_name_list) > 0:
            employees = ', '.join(employee_name_list)
            self.warning_message = "Attention : les consultant(e)s suivant(e)s ont au moins une ligne de pointage dont la valorisation en euros est nulle entre le %s et le %s : %s.\n\nVérifiez que cela est normal (exemple : consultant externes payés au mois) ou corrigez l'erreur avant de valider la création des clôtures comptables." %(begin_period.strftime('%d/%m/%Y'), self.date.strftime('%d/%m/%Y'), employees)
        else : 
            self.warning_message = False

    def _default_date(self):
        return datetime.date.today().replace(day=1) - datetime.timedelta(1) 

    def get_warning_analytic_lines(self):
        last_closing_of_older_not_closed_project = False
        for proj_id in self.project_ids:
            previous_accounting_closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', proj_id.id), ('closing_date', '<', self.date)], order="closing_date desc")
            if previous_accounting_closing_ids:
                prev_closing_date = previous_accounting_closing_ids[0].closing_date
                if not(last_closing_of_older_not_closed_project) or (last_closing_of_older_not_closed_project > prev_closing_date):
                    last_closing_of_older_not_closed_project = prev_closing_date

        if last_closing_of_older_not_closed_project :
            begin_period = min(last_closing_of_older_not_closed_project, self.date.replace(day=1))
        else :
            begin_period = self.date.replace(day=1)

        lines = self.env['account.analytic.line'].search([('company_id', '=', self.company_id.id), ('category', '=', 'project_employee_validated'), ('amount', '=', 0), ('unit_amount', '!=', 0), ('date', '>=', begin_period), ('date', '<=', self.date)])
        return lines, begin_period




    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date = fields.Date('Date de clôture', default=_default_date)
    project_ids = fields.Many2many('project.project', check_company=False)
    warning_message = fields.Text()



    def action_validate(self):
        _logger.info('-- wizardAccountingClosingMassCreation > action_validate')
        dic_list = []
        for project_id in self.project_ids:
            closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', project_id.id), ('closing_date', '=', self.date)])
            if len(closing_ids) == 0:
                dic = {
                        'project_id' : project_id.id,
                        'company_id' : project_id.company_id.id,
                        'closing_date' : self.date,
                }
                _logger.info(dic)
                dic_list.append(dic)
                _logger.info(dic)
        _logger.info(dic_list)
        self.env['project.accounting_closing'].create(dic_list)


    def action_open_warning_analytic_line(self):
        analytic_lines, begin_period = self.get_warning_analytic_lines()
        view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Feuille de temps',
                'res_model': 'account.analytic.line',
                'domain' : [('id', 'in', analytic_lines.ids)],
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'context': {},
                # if you want to open the form in edit mode direclty
                'flags': {'initial_mode': 'edit'},
                'target': 'current',
            }
