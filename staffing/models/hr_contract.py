from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import datetime


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_daily_cost(self, date):
        if self.is_daily_cost_overridden :
            return self.daily_cost, False
        else :
            cost_line = self.job_id._get_daily_cost_line(date)
            if not cost_line :
                _logger.info(_("Dayily cost not defined for this employee at this date : %s, %s." % (self.employee_id.name, date)))
                return 0.0, False
            return cost_line.cost, cost_line

    is_daily_cost_overridden = fields.Boolean("Surcharger le CJM du grade")
    daily_cost = fields.Float("CJM du contrat")
    work_location_id = fields.Many2one('hr.work.location', string="Bureau")
    productive_share = fields.Float("Part productive", default=100.0)


    def unlink(self):
        employee_id = self.employee_id.id
        date_start = self.date_start
        date_end = self.date_end

        res = super().unlink()
        self.refresh_analytic_lines(employee_id, date_start, date_end)
        self.refresh_employee_staffing_report(employee_id, date_start, date_end)

        return res

    def create(self, vals):
        res = super().create(vals)
        for rec in res :
            self.refresh_analytic_lines(rec.employee_id.id, rec.date_start, rec.date_end)
            self.refresh_employee_staffing_report(rec.employee_id.id, rec.date_start, rec.date_end)
        return res

    def write(self, vals):
        old_date_start = self.date_start
        old_date_end = self.date_end
        old_employee_id = self.employee_id.id
        res = super().write(vals)

        if not(old_date_end):
            old_date_end = datetime.date(2100,1,1)
        if not(self.date_end):
            new_date_end = datetime.date(2100,1,1)
        else :
            new_date_end = self.date_end

        start = min(old_date_start, self.date_start)
        end = max(old_date_end, new_date_end)

        if 'date_start' in vals or 'date_end' in vals or 'employee_id' in vals or 'is_daily_cost_overridden' in vals or 'daily_cost' in vals or 'job_id' in vals :
            self.refresh_analytic_lines(self.employee_id.id, start, end)
            if old_employee_id != self.employee_id.id:
                self.refresh_analytic_lines(old_employee_id, start, end)

        if 'productive_share' in vals :
            self.refresh_employee_staffing_report(self.employee_id.id, start, end)
            if old_employee_id != self.employee_id.id:
                self.refresh_employee_staffing_report(old_employee_id, start, end)

        return res


    def refresh_employee_staffing_report(self, employee_id, date_start, date_end):
        _logger.info('-- hr.contract > refresh_employee_staffing_report employee_id=%s date_start=%s date_end=%s' % (str(employee_id), str(date_start), str(date_end)))
        if not(date_end):
            date_end = datetime.date(2100,1,1)
        employee_staffing_reports = self.env['hr.employee_staffing_report'].search([('employee_id', '=', employee_id), ('end_date', '>=', date_start), ('start_date', '<=', date_end)])
        for report in employee_staffing_reports :
            report.availability()


    def refresh_analytic_lines(self, employee_id, date_start, date_end):
        _logger.info('-- hr.contract > refresh_analytic_lines employee_id=%s date_start=%s date_end=%s' % (str(employee_id), str(date_start), str(date_end)))
        if not(date_end):
            date_end = datetime.date(2100,1,1)
        lines = self.env['account.analytic.line'].search([('project_id', '!=', False), ('holiday_id', '=', False), ('employee_id', '=', employee_id), ('date', '>=', date_start), ('date', '<=', date_end)])
        for line in lines :
            line.refresh_amount()
