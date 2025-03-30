from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = "agreement"

    purchase_order_ids = fields.One2many('purchase.order', 'agreement_id')
