# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="Agreement",
        ondelete="restrict",
        domain=[('domain', '=', 'sale')],
        tracking=True,
        #readonly=True,
        copy=False,
    )

    agreement_type_id = fields.Many2one(
        comodel_name="agreement.type",
        related="agreement_id.agreement_type_id",
        string="Agreement Type",
        ondelete="restrict",
        tracking=True,
        copy=True,
    )

    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="agreement_id",
        string="Bons de commande",
    )
