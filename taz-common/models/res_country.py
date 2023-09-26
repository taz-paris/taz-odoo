from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class ResCountry(models.Model):
    _inherit = "res.country"

    address_format = fields.Text(
        default=(
            "%(street)s\n%(street2)s\n%(street3)s\n"
            "%(city)s %(state_code)s %(zip)s\n"
            "%(country_name)s"
        )
    )
