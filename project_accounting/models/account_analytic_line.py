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
        res = super().create(vals)
        self.update_project()
        return res

    def unlink(self):
        category = self.category
        project_id = self.project_id
        super().unlink()
        if category == 'project_employee_validated':
            #self.env['project.project'].search([('id', '=', project_id)])[0].compute()
            project_id.compute()

    def update_project(self):
        for rec in self:
            if rec.category != 'project_employee_validated':
                continue
            rec.project_id.compute()
