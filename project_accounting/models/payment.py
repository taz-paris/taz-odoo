from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class accountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_default_advance_sale_order_id(self):
        return self.env.context.get('default_advance_sale_order_id')

    def _get_default_partner_id(self):
        return self.env.context.get('default_partner_id')

    advance_sale_order_id = fields.Many2one('sale.order', string="Paiement d'avance pour la commande client", default=_get_default_advance_sale_order_id)#, domain=[('partner_id', '=', partner_id)])
    partner_id = fields.Many2one(default=_get_default_partner_id)
