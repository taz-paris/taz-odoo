from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class tazResSector(models.Model):
    _name = "res.partner.sector"

    name = fields.Char(string="Nom")
    partner_ids = fields.One2many('res.partner', 'sector_id')