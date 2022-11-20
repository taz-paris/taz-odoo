from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class ResPartnerIndustryPillar(models.Model):
     _description = "Industry pillar"
     _name = "res.partner.industry.pillar"
     _order = "name"

     name = fields.Char('Name', translate=True)
     full_name = fields.Char('Full Name', translate=True)
     active = fields.Boolean('Active', default=True)

