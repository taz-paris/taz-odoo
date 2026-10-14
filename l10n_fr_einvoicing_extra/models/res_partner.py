from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # l10n_fr_einvoicing only shows default_fr_directory_line_id on the
    # commercial entity itself, or on the child contact of type "invoice".
    # We need it available on any child contact, so the parent_id/type
    # condition is dropped here: call super() first, then widen the result
    # to any child whose commercial entity passes the entity_type/closed
    # checks.
    def _compute_fr_directory_line_show(self):
        super()._compute_fr_directory_line_show()
        for partner in self:
            cpartner = partner.commercial_partner_id
            if (
                cpartner.fr_directory_entity_type in ("private", "public")
                and not cpartner.fr_directory_closed
            ):
                partner.fr_directory_line_show = True
