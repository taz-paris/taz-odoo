from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # Champ technique, jamais affiché ni saisi : posé par le wizard de rapprochement sur les lignes « Consommé par… »
    # et « Dépassement… » ajoutées au BC du fournisseur « frais divers ». Il identifie ces lignes et leur facture
    # (retour arrière, statut « à facturer ») sans dépendre de leur libellé, qui reste libre.
    consumed_by_move_id = fields.Many2one(
        "account.move", string="Enveloppe consommée par", copy=False, index="btree_not_null", ondelete="cascade"
    )

    @api.depends(
        "order_id.partner_id", "company_id.expense_envelope_partner_id", "order_id.order_line.consumed_by_move_id"
    )
    def _compute_qty_invoiced(self):
        res = super()._compute_qty_invoiced()
        for line in self:
            partner = line.company_id.expense_envelope_partner_id
            if not partner or line.order_id.partner_id.commercial_partner_id != partner.commercial_partner_id:
                continue
            # Lignes de trace : jamais facturées. Lignes d'enveloppe : « rien à facturer » dès que le BC a été consommé
            # par une facture réelle (le BC suit alors le flux PA) ; un BC jamais consommé reste facturable normalement
            # par le fournisseur « frais divers ».
            if line.consumed_by_move_id or any(line.order_id.order_line.mapped("consumed_by_move_id")):
                line.qty_to_invoice = 0.0
        return res
