from odoo import models, api, fields, _
from odoo.exceptions import UserError
import logging
from odoo.osv import expression
from datetime import timedelta
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def adjust_grid(self, row_domain, column_field, col_domain, cell_field, change):
        """
        :param row_domain: domain matching the row
        :param column_field: name of the column field (e.g. 'date')
        :param col_domain: Full domain of the column (contains start/end dates)
        :param cell_field: name of the cell field (e.g. 'unit_amount')
        :param change: new value for the cell
        """
        # 1. Extraction of employee_id and project_id from row_domain
        equal_leaves = {}
        for leaf in row_domain:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[1] == '=':
                equal_leaves[leaf[0]] = leaf[2]
        if not 'employee_id' in equal_leaves.keys() :
            raise UserError(_("Impossible de déterminer l'employé pour cette ligne. Veuillez vérifier le regroupement."))
        if not 'project_id' in equal_leaves.keys() :
            raise UserError(_("Impossible de déterminer le projet pour cette ligne. Veuillez vérifier le regroupement."))

        # 2. Extraction of dates from col_domain
        start_date_str = False
        end_date_str = False
        if isinstance(col_domain, list):
            for leaf in col_domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == column_field:
                    if leaf[1] == '>=': start_date_str = leaf[2]
                    elif leaf[1] == '<=': end_date_str = leaf[2]
                    elif leaf[1] == '=': start_date_str = end_date_str = leaf[2]
        else:
            # Fallback for daily strings
            start_date_str = end_date_str = col_domain

        start_date = fields.Date.from_string(start_date_str)
        end_date = fields.Date.from_string(end_date_str) if end_date_str else start_date

        # 3. Find and Update records
        # Use intersection of row and col domains to respect all criteria (Date, Category, etc.)
        domain = expression.AND([row_domain, col_domain])
        records = self.search(domain)
        
        if records:
            current_total = sum(records.mapped(cell_field))
            if current_total > 0:
                factor = float(change) / current_total
                for r in records:
                    r.write({cell_field: r[cell_field] * factor})
            else:
                val_per_rec = float(change) / len(records)
                for r in records:
                    r.write({cell_field: val_per_rec})
        else:
            list_work_days_period = self.env['hr.employee'].browse(equal_leaves['employee_id']).list_work_days_period(start_date, end_date)
            #TODO : dans l'idéal, on devrait pouvoir récupérer la quotité de la journée réellement travaillée (hors absences) par journée (soit 0, soit 0,5 soit 1 dans notre modèle)
            total_worked_days = len(list_work_days_period)
            for work_day in list_work_days_period:
                vals = {
                    **equal_leaves,
                    cell_field: change/total_worked_days,
                    column_field: work_day,
                }
                self.create(vals)
                
        return True
