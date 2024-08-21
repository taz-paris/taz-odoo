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


    @api.onchange('date')
    def _onchange_date(self):
        self.project_ids = False
        p = self.env['project.project'].search([('number', '!=', False), ('company_id', '=', self.company_id.id), '|', ('has_provision_running', '=', True), ('stage_id.state', 'in', ['before_launch', 'launched'])])
        self.project_ids = p.ids

    def _default_date(self):
        return datetime.date.today().replace(day=1) - datetime.timedelta(1) 



    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date = fields.Date('Date de clôture', default=_default_date)
    project_ids = fields.Many2many('project.project', check_company=False)



    def action_validate(self):
        _logger.info('-- wizardAccountingClosingMassCreation > action_validate')
        for project_id in self.project_ids:
            closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', project_id.id), ('closing_date', '=', self.date)])
            if len(closing_ids) == 0:
                dic = {
                        'project_id' : project_id.id,
                        'company_id' : project_id.company_id.id,
                        'closing_date' : self.date,
                }
                _logger.info(dic)
                self.env['project.accounting_closing'].create(dic)
                _logger.info(dic)
