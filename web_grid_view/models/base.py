# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools import format_date
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
import datetime
import logging

_logger = logging.getLogger(__name__)

class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None, readonly_field=None):
        _logger.info(f"READ_GRID called with range: {range}")
        domain = domain or []
        
        # 1. Column Grouping
        column_info = self._grid_column_info(col_field, range)
        columns = column_info['values']
        
        # 2. Fetch Data
        grid_domain = expression.AND([domain, column_info['domain']])
        groupby = row_fields + [f"{col_field}:{column_info['format']}"]
        groups = self.read_group(grid_domain, [cell_field], groupby, lazy=False)
        
        # 3. Process Rows
        rows_map = {}
        for g in groups:
            row_key = []
            row_domain = []
            row_values = {}
            for f in row_fields:
                val = g[f]
                # Handle Many2one tuple (id, name)
                if isinstance(val, tuple):
                    row_key.append(val[0])
                    row_values[f] = val[1] # Display name
                    row_domain.append((f, '=', val[0]))
                elif val is False or val is None:
                    row_key.append(False)
                    row_values[f] = "" # Display empty string
                    row_domain.append((f, '=', False))
                else:
                    row_key.append(val)
                    row_values[f] = val
                    row_domain.append((f, '=', val))
            
            row_key = tuple(row_key)
            if row_key not in rows_map:
                rows_map[row_key] = {
                    'values': row_values, 
                    'domain': row_domain,
                    'key': row_key
                }

        sorted_rows = sorted(rows_map.values(), key=lambda x: str(x['key']))
        
        # 4. Build Grid and Totals
        grid = []
        row_totals = []
        col_totals = [0] * len(columns)
        grand_total = 0
        
        # Index groups for faster lookup
        # We use a composite key of row_key + col_value
        # Note: read_group with 'day' returns formatted date string (e.g. "27 Oct 2023")
        # But we generated columns with YYYY-MM-DD.
        # We need to match them. 
        # The group has '__domain' which contains the date range for that group.
        # We can extract the date from the domain!
        # Domain for date:day is usually [('date', '>=', '2023-10-27'), ('date', '<', '2023-10-28')]
        
        data_index = {}
        col_group_field = f"{col_field}:{column_info['format']}"
        
        for g in groups:
            r_key = []
            for f in row_fields:
                val = g[f]
                if isinstance(val, tuple):
                    r_key.append(val[0])
                else:
                    r_key.append(val)
            r_key = tuple(r_key)
            
            # Extract date from domain to match column
            # This is safer than relying on the string format
            g_domain = g.get('__domain', [])
            c_val = None
            for leaf in g_domain:
                if len(leaf) == 3 and leaf[0] == col_field and leaf[1] == '>=':
                    c_val = leaf[2] # This should be YYYY-MM-DD
                    break
            
            if c_val:
                data_index[(r_key, c_val)] = g

        for row in sorted_rows:
            row_cells = []
            r_total = 0
            for col_idx, col in enumerate(columns):
                # col['values'][col_field] is YYYY-MM-DD
                c_val = col['values'][col_field]
                
                group = data_index.get((row['key'], c_val))
                
                if group:
                    val = group.get(cell_field, 0)
                    cell = self._grid_format_cell(group, cell_field)
                else:
                    val = 0
                    cell = self._grid_make_empty_cell(row['domain'], col['domain'], [])
                
                row_cells.append(cell)
                
                # Totals
                r_total += val
                col_totals[col_idx] += val
                grand_total += val
            
            grid.append(row_cells)
            row_totals.append(r_total)

        return {
            'rows': sorted_rows,
            'cols': columns,
            'grid': grid,
            'row_totals': row_totals,
            'col_totals': col_totals,
            'grand_total': grand_total,
            'prev': column_info.get('prev'),
            'next': column_info.get('next'),
        }

    @api.model
    def _grid_column_info(self, name, range):
        if not range:
            range = {}
        
        span = range.get('span', 'month')
        anchor = range.get('anchor')
        
        today = fields.Date.context_today(self)
        if anchor:
            base_date = fields.Date.from_string(anchor)
        else:
            base_date = today

        if span == 'week':
            start_date = base_date - datetime.timedelta(days=base_date.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif span == 'month':
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        else:
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)

        columns = []
        current_date = start_date
        while current_date <= end_date:
            date_str = fields.Date.to_string(current_date)
            columns.append({
                'values': {name: date_str},
                'domain': [(name, '=', date_str)],
                'is_current': current_date == today,
                'label': format_date(self.env, current_date)
            })
            current_date += datetime.timedelta(days=1)

        prev_date = start_date - datetime.timedelta(days=1)
        next_date = end_date + datetime.timedelta(days=1)
        
        return {
            'values': columns,
            'domain': [(name, '>=', fields.Date.to_string(start_date)), (name, '<=', fields.Date.to_string(end_date))],
            'format': 'day',
            'prev': {'grid_anchor': fields.Date.to_string(prev_date)},
            'next': {'grid_anchor': fields.Date.to_string(next_date)}
        }

    @api.model
    def _grid_make_empty_cell(self, row_domain, column_domain, view_domain):
        return {
            'value': 0,
            'domain': expression.AND([row_domain, column_domain, view_domain]),
            'size': 0,
            'readonly': False,
            'classes': []
        }

    @api.model
    def _grid_format_cell(self, group, cell_field):
        return {
            'value': group.get(cell_field, 0),
            'domain': group.get('__domain', []),
            'size': group.get(f"{cell_field}_count", 0),
            'readonly': False,
        }
