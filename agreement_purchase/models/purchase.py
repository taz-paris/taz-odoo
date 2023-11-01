from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="Accord cadre fournisseur",
        ondelete="restrict",
        domain=[('domain', '=', 'purchase')],
        tracking=True,
        readonly=True,
        copy=False,
        states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
    )

    agreement_type_id = fields.Many2one(
        comodel_name="agreement.type",
        related="agreement_id.agreement_type_id",
        string="Type d'accord cadre fournisseur",
        ondelete="restrict",
        tracking=True,
        copy=True,
    )
