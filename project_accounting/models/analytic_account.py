from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class analyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def name_get(self):
        result = []
        for account in self:
            name = account.name
            if account.project_count > 0:
                name =  (account.project_ids[0]['number']+' ' or '') + account.name
            #TODO : que faire si cas exceptionnel avec plusieurs projets sur un même compte analytique ? Concaténer tous les numéros de projets ?
            result.append((account.id, name))
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        _logger.info('account.analytic.account => _name_search')
        query = "SELECT aaa.id, aaa.name FROM account_analytic_account AS aaa LEFT JOIN project_project AS p ON aaa.id = p.analytic_account_id WHERE aaa.name ilike %s OR p.number ilike %s;"
        name2 = '%'+str(name)+'%'
        params = (name2, name2)
        self.env.cr.execute(query, params)
        return [row[0] for row in self.env.cr.fetchall()]
