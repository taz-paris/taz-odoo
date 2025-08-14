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


    # Déclinaison du fichier purchase_sale_inter_company/models/account_move.py
    # pour que la sale.order.line soit liée à la account.move.line (ligne de la facture client) si l'on choisit de générer la facture fournissuer depuis le BCF 
    # (la validation de la facture fournisseur génèrera une facture client mirroir qui devra être liée à une sale.order.line)
    def _inter_company_create_invoice(self, dest_company):
        res = super()._inter_company_create_invoice(dest_company)
        if res["dest_invoice"].move_type in ["out_invoice", "out_refund"]:
            self._link_invoice_sale(res["dest_invoice"])
        # Le module purchase_sale_inter_company ne gérait pas les in_refund
        if res["dest_invoice"].move_type == "in_refund":
            self._link_invoice_purchase(res["dest_invoice"])
        return res

    def _link_invoice_sale(self, dest_invoice):
        self.ensure_one()
        for line in dest_invoice.invoice_line_ids:
            line.sale_line_ids = [(4, line.auto_invoice_line_id.purchase_line_id.intercompany_sale_line_id.id)]
        orders = dest_invoice.invoice_line_ids.sale_line_ids.order_id
        if orders:
            ref = "<a href=# data-oe-model=purchase.order data-oe-id={}>{}</a>"
            message = _("This customer bill/refund is related with: {}").format(
                ",".join([ref.format(o.id, o.name) for o in orders])
            )
            dest_invoice.message_post(body=message)

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
