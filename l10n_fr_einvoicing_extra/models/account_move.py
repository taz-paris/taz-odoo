from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Document-level EN16931 references with no dedicated field in
    # account_invoice_en16931/l10n_fr_account_invoice_en16931: each BT below
    # is 0..1 per invoice, so a plain field is enough (no need for a
    # generic N-to-1 reference model).
    l10n_fr_bt12_contract_reference = fields.Char(string="Référence du contrat (BT-12)")
    l10n_fr_bt15_receiving_advice_reference = fields.Char(
        string="Référence d'avis de réception (BT-15)"
    )
    l10n_fr_bt16_despatch_advice_reference = fields.Char(
        string="Référence d'avis d'expédition (BT-16)"
    )
    l10n_fr_bt17_tender_reference = fields.Char(
        string="Référence de l'appel d'offres ou du lot (BT-17)"
    )
    l10n_fr_bt18_invoiced_object_reference = fields.Char(
        string="Identifiant d'objet facturé (BT-18)"
    )
    l10n_fr_bt18_invoiced_object_scheme = fields.Char(
        string="Schéma de l'identifiant d'objet facturé (BT-18-1)"
    )
    l10n_fr_bt19_buyer_accounting_reference = fields.Char(
        string="Référence comptable de l'acheteur (BT-19)"
    )

    def _prepare_en16931_dict(self, speedy, pdf_invoice_bin=False):
        vals = super()._prepare_en16931_dict(speedy, pdf_invoice_bin=pdf_invoice_bin)
        project_numbers = [n for n in self.rel_project_ids.mapped("number") if n]
        if project_numbers:
            vals["BT-11"] = "/".join(project_numbers)
            project_names = [n for n in self.rel_project_ids.mapped("name") if n]
            if project_names:
                vals["BT-11-0"] = "/".join(project_names)
        if self.l10n_fr_bt12_contract_reference:
            vals["BT-12"] = self.l10n_fr_bt12_contract_reference
        if self.l10n_fr_bt15_receiving_advice_reference:
            vals["BT-15"] = self.l10n_fr_bt15_receiving_advice_reference
        if self.l10n_fr_bt16_despatch_advice_reference:
            vals["BT-16"] = self.l10n_fr_bt16_despatch_advice_reference
        if self.l10n_fr_bt17_tender_reference:
            # BT-17 is 0..n in the EXTENDED profile but capped to a single
            # element at en16931/CIUS-FR level; the library still expects a
            # list.
            vals["BT-17"] = [self.l10n_fr_bt17_tender_reference]
        if self.l10n_fr_bt18_invoiced_object_reference:
            # BT-18 is keyed by its scheme identifier (BT-18-1).
            scheme = self.l10n_fr_bt18_invoiced_object_scheme or ""
            vals["BT-18"] = {scheme: self.l10n_fr_bt18_invoiced_object_reference}
        if self.l10n_fr_bt19_buyer_accounting_reference:
            vals["BT-19"] = self.l10n_fr_bt19_buyer_accounting_reference
        return vals
