# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class tazResUsers(models.Model):
     _inherit = "res.users"

     def name_get(self):
         res = []
         for rec in self:
            res.append((rec.id, "%s %s" % (rec.first_name or "", rec.name or "")))
         return res

