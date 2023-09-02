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


    @api.onchange('date')
    def _onchange_date(self):
        self.project_ids = False
        #p = self.env['project.project'].search([('stage_id.state', 'in', ['before_launch', 'launched'])])
        #TODO : il faudrait mieux les projets (non TERMINES à cette DATE OU cloturés entre la DATE et le pointage précédent) ET (qui n'ont pas cloture postérieur ou égal à cette date)
        self.project_ids = p.ids
        self.project_ids = [1129] #projet test3.1

    def _default_date(self):
        return datetime.date.today().replace(day=1) - datetime.timedelta(1) 



    date = fields.Date('Date de clôture', default=_default_date)
    project_ids = fields.Many2many('project.project')



    def action_validate(self):
        for project_id in self.project_ids:
            closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', project_id.id), ('closing_date', '=', self.date)])
            if len(closing_ids) == 0:
                self.env['project.accounting_closing'].create({
                        'project_id' : project_id.id,
                        'closing_date' : self.date,
                    })
