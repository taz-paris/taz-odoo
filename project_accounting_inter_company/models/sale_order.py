from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_sale_purchase_line_sync_fields(self):
        """Map sale line fields to the synced purchase line peer"""
        return {
            "name" : "name",
            "product_uom_qty": "product_qty",
            "qty_delivered" : "qty_received",
            "previsional_invoice_date" : "previsional_invoice_date",
        }

    def write(self, vals):
        """Sync values of confirmed unlocked purchases"""
        res = super().write(vals)
        _logger.info(self.env.context)
        if self.env.context.get("stop_loop_sync_purchase_sale_orders") == True:
            return res
        sync_map = self._get_sale_purchase_line_sync_fields()
        update_vals = {
            sync_map.get(field): value
            for field, value in vals.items()
            if sync_map.get(field)
        }
        if not update_vals:
            return res
        intercompany_user = (
            self.auto_purchase_line_id.sudo().company_id.intercompany_sale_user_id
            or self.env.user
        )
        purchase_lines = self.auto_purchase_line_id.with_user(
            intercompany_user.id
        ).sudo()
        if not purchase_lines:
            return res
        closed_purchase_lines = purchase_lines.filtered(
            lambda x: x.state not in self._get_allowed_purchase_order_states()
        )
        if closed_purchase_lines:
            raise UserError(
                _(
                    "The related purchase orders with reference %(orders)s can't be "
                    "modified. They're either unconfirmed or locked for modifications.",
                    orders=",".join(closed_purchase_lines.order_id.mapped("name")),
                )
            )
        # Update directly the sale order so we can trigger the decreased qty exceptions
        for purchase in purchase_lines.order_id:
            purchase.with_context(stop_loop_sync_purchase_sale_orders=True).write(
                {
                    "order_line": [
                        (1, line.id, update_vals)
                        for line in purchase_lines.filtered(lambda x: x.order_id == purchase)
                    ]
                }
            )
        return res

    
    def _get_allowed_purchase_order_states(self):
        allowed_states = ["purchase"]
        if self.env.context.get("allow_update_locked_purchases", False):
            allowed_states.append("done")
        return allowed_states
