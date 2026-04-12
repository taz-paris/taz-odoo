from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

class Agreement(models.Model):
    _inherit = "agreement"

    def _get_total_order_amount(self):
        """Retourne le montant total commandé sur cet accord.
        Surchargé par agreement_purchase pour le domaine 'purchase'."""
        self.ensure_one()
        if self.domain == 'sale':
            orders = self.env['sale.order'].sudo().search([('agreement_id', '=', self.id)])
            return sum(o.amount_untaxed for o in orders)
        return 0.0

    @api.depends('max_amount')
    def compute(self):
        for rec in self:
            rec.total_order_amount = rec._get_total_order_amount()
            sold = rec.total_order_amount + rec.other_contractors_total_sale_order
            rec.available_amount = rec.max_amount - sold
            if rec.max_amount == 0.0:
                rec.sold_rate = 0.0
            else:
                rec.sold_rate = sold / rec.max_amount * 100

    total_order_amount = fields.Monetary("Montant commandé TF", compute=compute, compute_sudo=True)
    other_contractors_total_sale_order = fields.Monetary("Montant commandé hors TF", help="Montants commandés auprès des autres co-traitants.")
    available_amount = fields.Monetary("Montant restant engageable", compute=compute, compute_sudo=True)
    sold_rate = fields.Float("%age déjà engagé (€)", compute=compute, compute_sudo=True)

    sale_order_ids = fields.One2many('sale.order', 'agreement_id')
