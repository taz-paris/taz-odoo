from odoo import models, api

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        """
        Adjusts the grid cell value.
        :param row_domain: domain matching the row
        :param column_field: name of the column field (e.g. 'date')
        :param column_value: value of the column field (e.g. '2023-10-27')
        :param cell_field: name of the cell field (e.g. 'unit_amount')
        :param change: new value for the cell
        """
        # 1. Find existing record
        domain = row_domain + [(column_field, '=', column_value)]
        record = self.search(domain, limit=1)
        
        if record:
            record.write({cell_field: change})
        else:
            # 2. Create new record
            vals = {
                column_field: column_value,
                cell_field: change,
                'name': '/', # Default description
            }
            
            # Parse row_domain to extract project_id, task_id, etc.
            for leaf in row_domain:
                if len(leaf) == 3 and leaf[1] == '=':
                    vals[leaf[0]] = leaf[2]
            
            self.create(vals)
            
        return True
