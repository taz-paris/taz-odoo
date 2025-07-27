from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class analyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _order = 'display_name'

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name :
            domain += ['|', ('name', operator, name), ('display_name', operator, name)]
        return self._search(domain, limit=limit, order=order)

    @api.depends('project_ids', 'project_ids.number', 'project_ids.name', 'name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            if len(rec.project_ids)==1:
                rec.display_name = rec.project_ids[0].display_name
            else :
                rec.display_name = rec.name

    display_name = fields.Char(store=True)
