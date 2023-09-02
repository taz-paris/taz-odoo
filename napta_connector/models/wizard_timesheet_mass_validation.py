from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _
from odoo.addons.napta_connector.models.napta import ClientRestNapta
import datetime

import logging
_logger = logging.getLogger(__name__)

    
class wizardTimesheetMassValidation(models.TransientModel):
    _name = 'wizard_timesheet_mass_validation'
    _description = "wizard_timesheet_mass_validation"


    @api.onchange('date')
    def _onchange_date(self):
        t = self.env['account.analytic.line'].search([('napta_id', '!=', False), ('category', '=', 'project_employee_validated'), ('date', '<', self.date), ('is_timesheet_closed_on_napta', '=', False)]) 
        self.timesheet_period_ids = t.ids

    def _default_date(self):
        return datetime.date.today().replace(day=1) 

    date = fields.Date('Valider toutes les feuilles de temps STRICTEMENT antérieures au', default=_default_date)
    timesheet_period_ids = fields.Many2many('account.analytic.line', string="Feuilles de temps")

    def action_validate(self):
        self.env['project.project'].sudo().synchAllNapta()

        client = ClientRestNapta(self.env)

        for timesheet_period in self.timesheet_period_ids:
            timesheet_period_napta = client.read_cache('timesheet_period', timesheet_period.napta_id)
            timesheet_napta_id = timesheet_period_napta['attributes']['timesheet_id']
            attributes = {
                'closed' : True,
            }
            client.patch_api('timesheet', attributes, timesheet_napta_id)
            timesheet_period.is_timesheet_closed_on_napta = True
            self.env.cr.commit()
