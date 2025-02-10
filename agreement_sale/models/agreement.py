from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

class Agreement(models.Model):
    _inherit = "agreement"

    @api.depends('max_amount')
    def compute(self):
        for rec in self:
            # This is computed with sudo to include all orders of all companies, wathever companies are currently selected
            if rec.domain == 'sale':
                order_ids = self.env['sale.order'].sudo().search([('agreement_id', '=', rec.id)])
            elif rec.domain == 'purchase':
                order_ids = self.env['purchase.order'].sudo().search([('agreement_id', '=', rec.id)])
            else :
                raise ValidationError("Domaine de marché non géré : %s" % rec.domain)

            total_orders = 0
            for order in order_ids:
               total_orders += order.amount_untaxed
            rec.total_order_amount = total_orders

            sold = rec.total_order_amount + rec.other_contractors_total_sale_order 
            rec.available_amount = rec.max_amount - sold
            if rec.max_amount == 0.0:
                rec.sold_rate = 0.0
            else:
                rec.sold_rate = sold / rec.max_amount * 100

    total_order_amount = fields.Monetary("Montant commandé Galaxie", compute=compute, compute_sudo=True)
    other_contractors_total_sale_order = fields.Monetary("Montant commandé hors Galaxie", help="Montants commandés auprès des autres co-traitants.")
    available_amount = fields.Monetary("Montant restant engageable", compute=compute, compute_sudo=True)
    sold_rate = fields.Float("%age déjà engagé (€)", compute=compute, compute_sudo=True)
