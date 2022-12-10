from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class staffingEmployee(models.Model):
    _inherit = "hr.employee"

    def _sync_user(self, user, employee_has_image=False):
        _logger.info('_sync_user')
        vals  = super()._sync_user(user, employee_has_image) 
        _logger.info('_sync_user AFTER')
        if user.first_name :
            _logger.info('first_name' + str(user.first_name))
            vals['first_name'] = user.first_name
        return vals


    first_name = fields.Char(string="Prénom")





class staffingUsers(models.Model):
    _inherit = "res.users"

    def _get_employee_fields_to_sync(self):
        res = super()._get_employee_fields_to_sync()
        res.append('first_name')
        return res
