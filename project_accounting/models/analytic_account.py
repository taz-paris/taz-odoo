from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class analyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _order = 'display_name'

    def name_get(self):
        res = super().name_get()
        result = []
        for account in self:
            name = account.name
            if account.project_count > 0 :
                name =  (str(account.project_ids[0]['number'])+' ' or '') + account.name
            #TODO : que faire si cas exceptionnel avec plusieurs projets sur un même compte analytique ? Concaténer tous les numéros de projets ?
            result.append((account.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None, name_get_uid=None):
        domain = list(domain or [])
        if name :
            domain += ['|', ('name', operator, name), ('display_name', operator, name)]
        return self._search(domain, limit=limit, order=order, access_rights_uid=name_get_uid)


    @api.depends('project_ids', 'project_ids.number', 'project_ids.name', 'name')
    def _compute_display_name(self):
        for rec in self:
            if len(rec.project_ids)==1:
                rec.display_name = rec.project_ids[0].display_name
            else :
                rec.display_name = rec.name

    display_name = fields.Char(store=True)
