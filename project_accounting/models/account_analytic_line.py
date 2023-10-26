from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec.update_project()
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        self.update_project()
        return res

    def unlink(self):
        project_to_update = []
        for rec in self:
            if rec.category == 'project_employee_validated':
                if rec.project_id not in project_to_update:
                    project_to_update.append(rec.project_id)

        res = super().unlink()

        for project_id in project_to_update :
            project_id.compute()

        return res

    def update_project(self):
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
            rec.project_id.compute()
