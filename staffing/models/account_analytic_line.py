from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    def write(self, vals):
        vals = self._sync_project(vals)
        super().write(vals)

    def create(self, vals):
        res = []
        for val in vals:
            val = self._sync_project(val)
            res.append(val)
        super().create(res)

    def _sync_project(self, vals):
        #_logger.info(vals)
        #TODO : si le projet change, changer le staffing_need_id
        if 'staffing_need_id' in vals.keys():
            need = self.env['staffing.need'].browse([vals['staffing_need_id']])[0]
            vals['project_id'] = need.project_id.id
            vals['account_id'] = need.project_id.analytic_account_id.id
            vals['employee_id'] =  need.staffed_employee_id.id
        #_logger.info(vals)
        return vals

    category = fields.Selection(selection_add=[
            ('project_forecast', 'Prévisionnel'), 
            ('project_draft', 'Pointage brouillon'),
            ('project_employee_validated', 'Pointage validé par le consultant'),
        ])

    staffing_need_id = fields.Many2one('staffing.need', ondelete="restrict")
