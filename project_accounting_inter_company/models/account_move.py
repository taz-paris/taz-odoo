from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_account_move_line(self, dest_move, dest_company):
        _logger.info('==== _prepare_account_move_line')
        new_line = super()._prepare_account_move_line(dest_move, dest_company)
        new_line['analytic_distribution'] = self.env['purchase.order'].get_dest_analytic_distribution(self.analytic_distribution, dest_company)
        _logger.info(new_line)
        return new_line
