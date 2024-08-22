from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

from odoo.tools.misc import clean_context

class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_invoice_data(self, dest_company):
        self = self.with_context(clean_context(self.env.context))
        res = super()._prepare_invoice_data(dest_company)
        return res

    def _create_destination_account_move_line(self, dest_invoice, dest_company):
        self = self.with_context(clean_context(self.env.context))
        res = super()._create_destination_account_move_line(dest_invoice, dest_company)
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_account_move_line(self, dest_move, dest_company):
        _logger.info('==== _prepare_account_move_line')
        new_line = super()._prepare_account_move_line(dest_move, dest_company)
        if dest_move.move_type in ['in_invoice', 'in_refund']:
            new_line['analytic_distribution'] = self.env['purchase.order'].get_dest_analytic_distribution_from_supplier_company(self.analytic_distribution, dest_company, self.company_id)
        elif dest_move.move_type in ['out_invoice', 'out_refund']:
            new_line['analytic_distribution'] = self.env['purchase.order'].get_dest_analytic_distribution(self.analytic_distribution, dest_company, self.company_id)
        else :
            raise ValidationError(_("Type d'écriture non géré par le module project_accounting_inter_company : %s." % dest_move.move_type))
        return new_line
