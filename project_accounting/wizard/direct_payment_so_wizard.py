from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class directPaymentSO(models.TransientModel):
    _name = 'sale.direct_payment_wizard'
    _description = "Sales direct payment wizard"

    project_id = fields.Many2one('project.project', required=True)
    project_outsourcing_link_ids = fields.One2many(related='project_id.project_outsourcing_link_ids', required=True)
    sale_order_line = fields.Many2one('sale.order.line', required=True)

    new_po = fields.Selection([
            ('existing_po', 'Ajouter cette ligne à un BC fournisseur existant'),
            ('new_po', 'Créer sur un nouveau BC fournisseur'),
        ], string='Positionnement de la ligne')


    def create_direct_payment_line(self):
        for rec in self :
            
