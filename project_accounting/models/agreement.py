from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)



    
class Agreement(models.Model):
    _inherit = "agreement"

    project_ids = fields.One2many('project.project', 'agreement_id') 
    signature_date = fields.Date(string="Date de notification/signature")
