from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def write(self, vals):
        _logger.info('---------- write account.analytic.line project_accounting/model/account_analytic_line.py')
        if not('amount' in vals.keys () or 'date' in vals.keys() or 'date_end' in vals.keys() or 'project_id' in vals.keys() or 'category' in vals.keys()):
            return super().write(vals)

        if 'project_id' in vals.keys():
            # si le project_id change il faut appeler update_project *avant* et après l'enregistrement de l'analytic.line pour que les deux projets soient à jour
            self.update_project()
        res = super().write(vals)
        self.update_project()
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        self.update_project()
        return res

    def unlink(self):
        for rec in self:
            if rec.category == 'project_employee_validated':
                rec.project_id.has_to_be_recomputed = True

        res = super().unlink()

        if self.env.context.get('do_not_update_project') != True:
            self.env['project.project'].recompute_if_has_to_be_recomputed()

        return res

    def update_project(self):
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
            rec.project_id.has_to_be_recomputed = True
            if self.env.context.get('do_not_update_project') != True:
                self.env['project.project'].recompute_if_has_to_be_recomputed()
