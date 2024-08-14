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
        if dest_move.move_type in ['in_invoice', 'in_refund']:
            new_line['analytic_distribution'] = self.env['purchase.order'].get_dest_analytic_distribution_from_supplier_company(self.analytic_distribution, dest_company, self.company_id)
        elif dest_move.move_type in ['out_invoice', 'out_refund']:
            new_line['analytic_distribution'] = self.env['purchase.order'].get_dest_analytic_distribution(self.analytic_distribution, dest_company)
        else :
            raise ValidationError(_("Type d'écriture non géré par le module project_accounting_inter_company."))
        return new_line
