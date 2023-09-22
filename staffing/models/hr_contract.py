from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)



class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_daily_cost(self, date):
        if self.is_daily_cost_overridden :
            return self.daily_cost, False
        else :
            cost_line = self._get_daily_cost(date)
            if not cost_line :
                _logger.info(_("Dayily cost not defined for this employee at this date : %s, %s." % (self.employee_id.name, date)))
            return cost_line.cost, cost_line

    is_daily_cost_overridden = fields.Boolean("Surcharger le CJM du grade")
    daily_cost = fields.Float("CJM du contrat")
