from odoo import _, api, fields, models


class AgreementSubcontractor(models.Model):
    _inherit = "agreement.subcontractor"

    """
    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="agreement_id"
    )
    """
