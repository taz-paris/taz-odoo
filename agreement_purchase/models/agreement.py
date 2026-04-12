from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = "agreement"

    def _get_total_order_amount(self):
        self.ensure_one()
        if self.domain == 'purchase':
            orders = self.env['purchase.order'].sudo().search([('agreement_id', '=', self.id)])
            return sum(o.amount_untaxed for o in orders)
        return super()._get_total_order_amount()

    purchase_order_ids = fields.One2many('purchase.order', 'agreement_id')
