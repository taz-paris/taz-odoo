from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fr_ctc_accredited_platform = fields.Selection(
        selection_add=[("einvoicing_router", "eInvoicing Router")],
        ondelete={"einvoicing_router": "set default"},
    )
