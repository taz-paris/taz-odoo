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
    allowed_states = self._get_allowed_sale_order_states()
    for order in lines.order_id.filtered(
        lambda x: x.intercompany_sale_order_id
    ):
        if order.intercompany_sale_order_id.sudo().state not in allowed_states:
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
        for purchase_line in lines.filtered(lambda x: x.order_id == order):
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


PurchaseOrderLine_inherit.create = create
