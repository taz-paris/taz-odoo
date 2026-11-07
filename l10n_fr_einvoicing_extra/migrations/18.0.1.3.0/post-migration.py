from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Recalcule la quantité à facturer des lignes de BC existantes du fournisseur « frais divers »."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([("expense_envelope_partner_id", "!=", False)]):
        company._recompute_envelope_lines(company.expense_envelope_partner_id)
