from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    #Augmentation de la précision décimale pour unit Amount car Napta découpe automatiquement les saisies par jour, ce qui peut générer des montants à plus de 2 décimales
    unit_amount = fields.Float(digits=(18,8))
    amount = fields.Float(digits=(13,3))
