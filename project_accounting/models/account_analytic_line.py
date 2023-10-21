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
        self.update_project()
        return res

    @api.model
    def create(self, vals):
        res = super().create(res)
        self.update_project()
        return res

    def unlink(self):
        category = self.category
        project_id = self.project_id
        self.unlink()
        if category == 'project_employee_validated':
            project_id.compute()

    def update_project(self):
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
            rec.project_id.compute()
