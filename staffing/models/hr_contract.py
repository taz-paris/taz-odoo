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
            #TODO : il va falloir gérer la mise à jour auto des lignes de pointage sur la durée du contrat si on change la valeur du daily_cost du contrat ou qu'on active/désactive le débrayage
            #       ... et quid si on change les date de début/fin du contrat ?
        else :
            cost_line = self.job_id._get_daily_cost_line(date)
            if not cost_line :
                _logger.info(_("Dayily cost not defined for this employee at this date : %s, %s." % (self.employee_id.name, date)))
            return cost_line.cost, cost_line

    is_daily_cost_overridden = fields.Boolean("Surcharger le CJM du grade")
    daily_cost = fields.Float("CJM du contrat")
