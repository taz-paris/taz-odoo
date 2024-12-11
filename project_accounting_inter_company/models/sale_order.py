from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_purchase_order_line_data(self, sale_line, dest_company, purchase_order):
        """Generate the Purchase Order Line values from the SO line
        :param sale_line : the origin Sale Order Line
        :rtype sale_line : sale.order.line record
        :param dest_company : the company of the created PO
        :rtype dest_company : res.company record
        :param purchase_order : the Purchase Order
        """
        new_line = self.env["purchase.order.line"].new(
            {
                "order_id": purchase_order.id,
                "product_id": sale_line.product_id.id,
                "product_uom": sale_line.product_uom.id,
                "product_qty": sale_line.product_uom_qty,
                "display_type": sale_line.display_type,
                "name": sale_line.name,
                "qty_received" : sale_line.qty_delivered,
                "previsional_invoice_date" : sale_line.previsional_invoice_date,
                "analytic_distribution" : self.env['purchase.order'].get_dest_analytic_distribution_from_supplier_company(sale_line.analytic_distribution, dest_company, self.company_id),
                "price_unit" : sale_line.price_unit,
            }
        )
        #for onchange_method in new_line._onchange_methods["product_id"]:
        #    onchange_method(new_line)
        new_line.update({"product_uom": sale_line.product_uom.id})
        #_logger.info('PREPARE POL LINE DATA')
        #_logger.info(new_line)
        #_logger.info(new_line._convert_to_write(new_line._cache))
        return new_line._convert_to_write(new_line._cache)



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_sale_purchase_line_sync_fields(self):
        """Map sale line fields to the synced purchase line peer"""
        return {
            "name" : "name",
            "product_id" : "product_id",
            "product_uom" : "product_uom", 
            "price_unit" : "price_unit",
            "product_uom_qty": "product_qty",
            "qty_delivered" : "qty_received",
            "previsional_invoice_date" : "previsional_invoice_date",
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Sync lines between an confirmed unlocked sale order and a confirmed unlocked
        purchase order"""
        lines = super().create(vals_list)
        _logger.info(self.env.context)
        if self.env.context.get("stop_loop_create_purchase_order_lines") == True:
            return lines
        allowed_states = self._get_allowed_purchase_order_states()
        for order in lines.order_id.filtered(
            lambda x: x.auto_purchase_order_id
        ):
            if order.auto_purchase_order_id.sudo().state not in allowed_states:
                raise UserError(
                    _(
                        "You can't change this purchase order as the corresponding "
                        "sale is %(state)s",
                        state=order.state,
                    )
                )
            intercompany_user = (
                order.auto_purchase_order_id.sudo().company_id.intercompany_sale_user_id
                or self.env.user
            )
            for sale_line in lines.filtered(lambda x: x.order_id == order):
                pol = self.env["purchase.order.line"].with_user(intercompany_user.id).with_context(stop_loop_create_purchase_order_lines=True).sudo().create(
                    order._prepare_purchase_order_line_data(
                        sale_line,
                        order.auto_purchase_order_id.sudo().company_id,
                        order.auto_purchase_order_id.sudo(),
                    )
                )
                sale_line.auto_purchase_line_id = pol.id

        return lines

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
        allowed_states = ["draft", "purchase"]
        if self.env.context.get("allow_update_locked_purchases", False):
            allowed_states.append("done")
        return allowed_states
