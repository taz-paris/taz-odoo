from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectStage(models.Model):
    _inherit = "project.project.stage"

    is_part_of_booking = fields.Boolean('Compte dans le book', help="Les projects qui sont à cette étape comptent dans le book.")

