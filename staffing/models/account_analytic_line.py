from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    def write(self, vals):
        vals = self._sync_project(vals)
        super().write(vals)

    def create(self, vals):
        res = []
        for val in vals:
            val = self._sync_project(val)
            res.append(val)
        super().create(res)

    def _sync_project(self, vals):
        #_logger.info(vals)
        #TODO : si le projet change, changer le staffing_need_id
        if 'staffing_need_id' in vals.keys():
            need = self.env['staffing.need'].browse([vals['staffing_need_id']])[0]
            vals['project_id'] = need.project_id.id
            vals['account_id'] = need.project_id.analytic_account_id.id
            vals['employee_id'] =  need.staffed_employee_id.id
        #_logger.info(vals)
        return vals

    category = fields.Selection(selection_add=[
            ('project_forecast', 'Prévisionnel'), 
            ('project_draft', 'Pointage brouillon'),
            ('project_employee_validated', 'Pointage validé par le consultant'),
        ])

    staffing_need_id = fields.Many2one('staffing.need', ondelete="restrict")


    #override to deal with uom in days
    #odoo/addons/hr_timesheet/models/hr_timesheet.py
    def _timesheet_postprocess_values(self, values):
        """ Get the addionnal values to write on record
            :param dict values: values for the model's fields, as a dictionary::
                {'field_name': field_value, ...}
            :return: a dictionary mapping each record id to its corresponding
                dictionary values to write (may be empty).
        """
        result = {id_: {} for id_ in self.ids}
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        # (re)compute the amount (depending on unit_amount, employee_id for the cost, and account_id for currency)
        if any(field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id', 'encoding_uom_id', 'holiday_id']):
            for timesheet in sudo_self:
                if timesheet.holiday_id :
                    continue

                encoding_uom_id = self.env.company.timesheet_encode_uom_id
                if encoding_uom_id == self.env.ref("uom.product_uom_hour"):
                    cost = timesheet._hourly_cost()
                elif encoding_uom_id == self.env.ref("uom.product_uom_day"):
                    cost = timesheet.employee_id._get_daily_cost(timesheet.date) 
                    if not cost :
                        raise ValidationError(_("Dayily cost not defined for this employee at this date."))
                else : 
                    raise ValidationError(_("Company timesheet encoding uom should be either Hours or Days."))

                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount, timesheet.account_id.currency_id or timesheet.currency_id, self.env.company, timesheet.date)
                result[timesheet.id].update({
                    'amount': amount_converted,
                })
        return result

