from odoo import fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    fr_ctc_accredited_platform = fields.Selection(
        selection_add=[("einvoicing_router", "eInvoicing Router")],
        ondelete={"einvoicing_router": "set default"},
    )

    def _fr_ctc_get_session(self):
        self.ensure_one()
        if self.fr_ctc_accredited_platform == "einvoicing_router":
            self._update_einvoicing_router_platform_urls()
        return super()._fr_ctc_get_session()

    def _update_einvoicing_router_platform_urls(self):
        from ..pyfrctc_platforms import PLATFORMS  # noqa: PLC0415

        root_url = (
            self.env["ir.config_parameter"].sudo().get_param("einvoicing_router_root_url")
        )
        if not root_url:
            raise UserError(
                self.env._(
                    "System parameter 'einvoicing_router_root_url' is not set. "
                    "It is required to use the 'eInvoicing Router' platform."
                )
            )
        root_url = root_url.rstrip("/")
        PLATFORMS["einvoicing_router"].update(
            {
                "afnor_base_url": f"{root_url}/api/afnor",
                "token_url": f"{root_url}/api/afnor/oauth/token",
            }
        )
