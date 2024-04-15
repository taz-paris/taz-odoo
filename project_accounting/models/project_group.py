from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectGroup(models.Model):
    _name = 'project.group'
    _description = 'A project group is use for data consolidation purpose'
    _check_company_auto = True
    _order = 'name asc'

    @api.depends('project_ids.stage_id.state')
    def compute(self):
        _logger.info('---- projectGroup compute')
        for rec in self:
            active = False
            for project in rec.project_ids:
                if project.stage_id.state != 'closed':
                    active=True
                    break
            rec.active = active
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    name = fields.Char('Nom', required=True)
    project_ids = fields.One2many('project.project', 'project_group_id', string="Projets")
    description = fields.Html("Description")

    active = fields.Boolean("Actif", compute=compute, store=True)
