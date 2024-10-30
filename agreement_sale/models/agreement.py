from odoo import _, api, fields, models

class Agreement(models.Model):
    _inherit = "agreement"

    @api.depends(
        # 'sale_order_ids',
        # 'sale_order_ids.amount_untaxed',
        'max_amount'
    )
    def compute(self):
        for rec in self:
            total_sale_order = 0
            for sale_order in rec.sale_order_ids:
               total_sale_order+= sale_order.amount_untaxed
            rec.total_sale_order = total_sale_order

            rec.available_amount = rec.max_amount - rec.total_sale_order - rec.other_contractors_total_sale_order
            # pourcentage engagé

    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="agreement_id",
        string="Bons de commande",
    )


    available_amount = fields.Monetary("Montant restant engageable", compute=compute)
    total_sale_order = fields.Monetary("Montant commandé", compute=compute)