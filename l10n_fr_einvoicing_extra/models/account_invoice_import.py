import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    def prepare_facturx_xpath_dict(self):
        xpathd = super().prepare_facturx_xpath_dict()
        # BT-13 (référence de commande) : la clé "origin" alimente account.move.invoice_origin
        xpathd["origin"] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:BuyerOrderReferencedDocument"
            "/ram:IssuerAssignedID"
        ]
        # BT-11 (référence de projet) : rapprochée du numéro de projet dans _post_process_invoice
        xpathd["project_reference"] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:SpecifiedProcurementProject"
            "/ram:ID"
        ]
        return xpathd

    @api.model
    def _find_project_from_references(self, parsed_inv):
        """BT-11 en priorité, sinon BT-13 : le contenu est comparé à project.project.number
        (unique en base). Une valeur absente, inconnue ou à plusieurs numéros ne donne aucun projet."""
        for key in ("project_reference", "origin"):
            value = (parsed_inv.get(key) or "").strip()
            if not value:
                continue
            project = self.env["project.project"].search([("number", "=", value)], limit=1)
            if project:
                return project
        return self.env["project.project"]

    @api.model
    def _post_process_invoice(self, parsed_inv, import_config, invoice):
        res = super()._post_process_invoice(parsed_inv, import_config, invoice)
        if parsed_inv.get("type") in ("out_invoice", "out_refund"):
            return res
        project = self._find_project_from_references(parsed_inv)
        if project and project.account_id:
            # Seules les lignes sans distribution analytique sont renseignées : la facture reçue
            # (quantités, prix, unités) n'est pas modifiée ; rel_project_ids de la facture se remplit.
            lines = invoice.invoice_line_ids.filtered(
                lambda line: line.display_type == "product" and not line.analytic_distribution
            )
            lines.write({"analytic_distribution": {str(project.account_id.id): 100}})
            invoice.message_post(
                body=self.env._(
                    "Project %(project)s deduced from the supplier references (BT-11 / BT-13).",
                    project=project.display_name,
                )
            )
        return res
