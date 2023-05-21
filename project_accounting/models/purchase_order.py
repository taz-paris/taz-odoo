from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import json
import logging
_logger = logging.getLogger(__name__)



class projectAccountingPurchaseOrder(models.Model):
    _inherit = "purchase.order"



class projectAccountingPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.constrains('direct_payment_sale_order_line_id', 'analytic_distribution', 'price_subtotal')
    def check(self):
        _logger.info('-- purchase.order.line CHECK')
        for rec in self:
            if rec.direct_payment_sale_order_line_id:
                if rec.analytic_distribution != rec.direct_payment_sale_order_line_id.analytic_distribution or rec.price_subtotal != rec.direct_payment_sale_order_line_id.price_subtotal:
                    raise ValidationError(_("L'une des lignes portant un paiement direct est incohérente (ex : la distribution analytique a plsuieurs compte ou bien elle n'est pas à 100%).\n\nUne fois que le paiement direct est engistré sur ligne du bon de commande du CLIENT FINAL, il n'est plus possible de modifier la distribution analytic, ni le sous-total de la ligne correspondante du BC de sous-traitance. \nVous devez supprimer le lien dans le bon de commande du client final si vous souhaitez la modifier."))


    direct_payment_sale_order_line_id = fields.One2many('sale.order.line', 'direct_payment_purchase_order_line_id',
            string="Paiement direct",
            help = "Ligne de la commande du client final")

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state', 'direct_payment_sale_order_line_id')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.direct_payment_sale_order_line_id :
                line.qty_to_invoice = 0
