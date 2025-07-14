from odoo import models, fields, api
from odoo.addons.purchase_sale_inter_company.models.purchase_order_line import PurchaseOrderLine as PurchaseOrderLine_inherit

import logging
_logger = logging.getLogger(__name__)


@api.model_create_multi
def create(self, vals_list):
    #_logger.info('OVERRIDE CREATE POL on monkey patch')
    #_logger.info(vals_list)
    lines = super(PurchaseOrderLine_inherit, self).create(vals_list)
    if self.env.context.get("stop_loop_create_purchase_order_lines") == True:
        return lines
    for order in lines.order_id.filtered(
        lambda x: x.intercompany_sale_order_id
    ):
        if order.intercompany_sale_order_id.sudo().state in {"cancel", "done"}:
            raise UserError(
                _(
                    "You can't change this purchase order as the corresponding "
                    "sale is %(state)s",
                    state=order.state,
                )
            )
        intercompany_user = (
            order.intercompany_sale_order_id.sudo().company_id.intercompany_sale_user_id
            or self.env.user
        )
        sale_lines = []
        for purchase_line in lines.filtered(lambda x, o=order: x.order_id == o):
            sale_lines.append(
                order._prepare_sale_order_line_data(
                    purchase_line,
                    order.intercompany_sale_order_id.sudo().company_id,
                    order.intercompany_sale_order_id.sudo(),
                )
            )
        self.env["sale.order.line"].with_user(intercompany_user.id).with_context(stop_loop_create_purchase_order_lines=True).sudo().create(
            sale_lines
        )
    return lines



def write(self, vals):
    """Sync values of confirmed unlocked sales"""
    res = super(PurchaseOrderLine_inherit, self).write(vals)
    sync_map = self._get_purchase_sale_line_sync_fields()
    update_vals = {
        sync_map.get(field): value
        for field, value in vals.items()
        if sync_map.get(field)
    }
    if not update_vals:
        return res
    intercompany_user = (
        self.intercompany_sale_line_id.sudo().company_id.intercompany_sale_user_id
        or self.env.user
    )
    sale_lines = self.intercompany_sale_line_id.with_user(
        intercompany_user.id
    ).sudo()
    if not sale_lines:
        return res
    closed_sale_lines = sale_lines.filtered(lambda x: x.state not in ["sale", "draft"])
    if closed_sale_lines:
        raise UserError(
            _(
                "The generated sale orders with reference %(orders)s can't be "
                "modified. They're either unconfirmed or locked for modifications.",
                orders=",".join(closed_sale_lines.order_id.mapped("name")),
            )
        )
    # Update directly the sale order so we can trigger the decreased qty exceptions
    for sale in sale_lines.order_id:
        sale.write(
            {
                "order_line": [
                    (1, line.id, update_vals)
                    for line in sale_lines.filtered(
                        lambda x, s=sale: x.order_id == s
                    )
                ]
            }
        )
    return res

PurchaseOrderLine_inherit.create = create
PurchaseOrderLine_inherit.write = write
