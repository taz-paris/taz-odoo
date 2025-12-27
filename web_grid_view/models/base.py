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
    def read_grid(self, row_fields, col_field, cell_field, domain=None, grid_range=None, readonly_field=None):
        _logger.info(f"READ_GRID called with range: {grid_range}")
        domain = domain or []
        
        # 1. Column Grouping
        column_info = self._grid_column_info(col_field, grid_range)
        columns = column_info['values']
        
        # 2. Fetch Data for all levels
        # We MUST use the grid_domain (which includes date filters) to avoid fetching too much data
        grid_domain = expression.AND([domain, column_info['domain']])
        
        all_groups = []
        for i in range(1, len(row_fields) + 1):
            current_row_fields = row_fields[:i]
            groupby = current_row_fields + [f"{col_field}:{column_info['format']}"]
            groups = self.read_group(grid_domain, [cell_field], groupby, lazy=False)
            # Add level info to groups
            for g in groups:
                g['__level'] = i
            all_groups.extend(groups)
            
        # 3. Process Groups into a flat list of rows with their grid data
        rows_data = {}
        
        for g in all_groups:
            level = g['__level']
            row_key_list = []
            row_values = {}
            for f in row_fields[:level]:
                val = g[f]
                if isinstance(val, tuple):
                    row_key_list.append(val[0])
                    row_values[f] = val[1]
                else:
                    row_key_list.append(val)
                    row_values[f] = val
            
            row_key = (level, tuple(row_key_list))
            
            if row_key not in rows_data:
                # Initialize grid with empty cell objects
                grid = []
                for col in columns:
                    # Construct domain for this cell
                    cell_row_domain = []
                    for f_idx, f in enumerate(row_fields[:level]):
                        cell_row_domain.append((f, '=', row_key_list[f_idx]))
                    
                    grid.append({
                        'value': 0,
                        'domain': expression.AND([domain, cell_row_domain, col['domain']]),
                        'readonly': level < len(row_fields) # Parent rows are readonly
                    })

                rows_data[row_key] = {
                    'level': level,
                    'values': row_values,
                    'full_key': row_key_list,
                    'grid': grid,
                    'row_total': 0,
                    'is_leaf': level == len(row_fields)
                }
            
            # Match group to column
            g_domain = g.get('__domain', [])
            c_val = None
            for leaf in g_domain:
                if len(leaf) == 3 and leaf[0] == col_field and leaf[1] == '>=':
                    c_val = leaf[2]
                    break
            
            if c_val:
                # Find column index
                for col_idx, col in enumerate(columns):
                    if col['values'][col_field] == c_val:
                        val = g.get(cell_field, 0)
                        rows_data[row_key]['grid'][col_idx]['value'] = val
                        rows_data[row_key]['row_total'] += val
                        break

        # 4. Calculate Column Totals and Grand Total (using level 1 groups)
        col_totals = [0] * len(columns)
        grand_total = 0
        
        level_1_rows = [r for r in rows_data.values() if r['level'] == 1]
        for r in level_1_rows:
            for i, cell in enumerate(r['grid']):
                col_totals[i] += cell['value']
            grand_total += r['row_total']

        # Round all totals
        for r in rows_data.values():
            r['row_total'] = round(r['row_total'], 10)
            for cell in r['grid']:
                cell['value'] = round(cell['value'], 10)
        
        col_totals = [round(v, 10) for v in col_totals]
        grand_total = round(grand_total, 10)

        # Sort rows
        sorted_rows = sorted(rows_data.values(), key=lambda x: (x['level'], str(x['values'])))

        return {
            'rows': sorted_rows,
            'cols': columns,
            'col_totals': col_totals,
            'grand_total': grand_total,
            'prev': column_info.get('prev'),
            'next': column_info.get('next'),
        }

    @api.model
    def _grid_column_info(self, name, grid_range):
        if not grid_range:
            grid_range = {}
        
        span = grid_range.get('span', 'month')
        anchor = grid_range.get('anchor')
        
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
