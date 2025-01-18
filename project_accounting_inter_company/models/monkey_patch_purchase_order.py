from odoo import models, fields, api
from odoo.addons.purchase_sale_inter_company.models.purchase_order import PurchaseOrder as PurchaseOrder_inherit

import logging
_logger = logging.getLogger(__name__)



def _inter_company_create_sale_order(self, dest_company):
    """Create a Sale Order from the current PO (self)
    Note : In this method, reading the current PO is done as sudo,
    and the creation of the derived
    SO as intercompany_user, minimizing the access right required
    for the trigger user.
    :param dest_company : the company of the created PO
    :rtype dest_company : res.company record
    """
    self.ensure_one()
    # Check intercompany user
    intercompany_user = dest_company.intercompany_sale_user_id
    if not intercompany_user:
        intercompany_user = self.env.user
    # check intercompany product
    self._check_intercompany_product(dest_company)
    # Accessing to selling partner with selling user, so data like
    # property_account_position can be retrieved
    company_partner = self.company_id.partner_id
    # check pricelist currency should be same with PO/SO document
    if self.currency_id.id != (
        company_partner.property_product_pricelist.currency_id.id
    ):
        raise UserError(
            _(
                "You cannot create SO from PO because "
                "sale price list currency is different than "
                "purchase price list currency."
            )
        )
    # create the SO and generate its lines from the PO lines
    sale_order_data = self._prepare_sale_order_data(
        self.name, company_partner, dest_company, self.dest_address_id
    )
    sale_order = (
        self.env["sale.order"]
        .with_user(intercompany_user.id)
        .sudo()
        .create(sale_order_data)
    )
    for purchase_line in self.order_line:
        sale_line_data = self._prepare_sale_order_line_data(
            purchase_line, dest_company, sale_order
        )
        self.env["sale.order.line"].with_user(intercompany_user.id).with_context(stop_loop_create_purchase_order_lines=True).sudo().create(
            sale_line_data
        )
    # write supplier reference field on PO
    if not self.partner_ref:
        self.partner_ref = sale_order.name
    # Validation of sale order
    if dest_company.sale_auto_validation:
        sale_order.with_user(intercompany_user.id).sudo().action_confirm()


PurchaseOrder_inherit._inter_company_create_sale_order = _inter_company_create_sale_order
