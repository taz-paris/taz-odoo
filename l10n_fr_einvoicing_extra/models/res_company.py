from odoo import fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_envelope_partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur « frais divers »",
        domain="[('is_company', '=', True)]",
        help="Fournisseur fictif porteur des enveloppes de frais prévus sur les projets (hôtels, restaurants...) "
        "chez des fournisseurs encore inconnus. Au rapprochement d'une facture, l'utilisateur peut consommer "
        "la ligne de BC de ce fournisseur pour le projet.",
    )

    fr_ctc_accredited_platform = fields.Selection(
        selection_add=[("einvoicing_router", "eInvoicing Router")],
        ondelete={"einvoicing_router": "set default"},
    )

    def write(self, vals):
        old_partners = {}
        if "expense_envelope_partner_id" in vals:
            old_partners = {c.id: c.expense_envelope_partner_id for c in self}
        res = super().write(vals)
        if "expense_envelope_partner_id" in vals:
            for company in self:
                company._recompute_envelope_lines(old_partners[company.id] | company.expense_envelope_partner_id)
        return res

    def _recompute_envelope_lines(self, partners):
        """Les lignes de BC déjà existantes du fournisseur « frais divers » (ancien et nouveau) sont recalculées :
        leur quantité à facturer passe à 0 (ou est rétablie si le fournisseur n'est plus désigné)."""
        self.ensure_one()
        if not partners:
            return
        Line = self.env["purchase.order.line"]
        lines = Line.sudo().search(
            [
                ("company_id", "=", self.id),
                ("order_id.partner_id.commercial_partner_id", "in", partners.commercial_partner_id.ids),
            ]
        )
        self.env.add_to_compute(Line._fields["qty_invoiced"], lines)

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
