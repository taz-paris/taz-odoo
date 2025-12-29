# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools import format_date
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
import datetime
import logging
import json

_logger = logging.getLogger(__name__)

class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, grid_range=None, readonly_field=None, orderby=None):
        _logger.info(f"READ_GRID called with range: {grid_range}")
        domain = domain or []
        
        # 1. Column Grouping
        column_info = self._grid_column_info(col_field, grid_range)
        columns = column_info['values']
        
        # 2. Fetch Data for all levels
        grid_domain = expression.AND([domain, column_info['domain']])
        
        all_groups = []
        for i in range(1, len(row_fields) + 1):
            current_row_fields = row_fields[:i]
            # Use the format specified in column_info
            groupby = current_row_fields + [f"{col_field}:{column_info['format']}"]
            
            current_orderby = None
            if orderby:
                sort_field = orderby.split(' ')[0]
                sort_order = orderby.split(' ')[1] if ' ' in orderby else 'asc'
                if sort_field in current_row_fields:
                    current_orderby = f"{sort_field} {sort_order}"

            groups = self.read_group(grid_domain, [cell_field], groupby, lazy=False, orderby=current_orderby)
            
            # DEBUG: Log groups to a specific file to be sure we see them
            try:
                with open('/tmp/grid_debug.log', 'a') as f:
                    f.write(f"\n--- Level {i} Groupby {groupby} ---\n")
                    for g in groups:
                        # Serialize safely
                        clean_g = {k: str(v) for k, v in g.items() if k != '__domain'}
                        f.write(f"Group: {clean_g} | Domain: {g.get('__domain')}\n")
            except:
                pass

            for g in groups:
                g['__level'] = i
            all_groups.extend(groups)
            
        # 3. Process Groups into a flat list of rows with their grid data
        rows_data = {}
        
        def normalize_date(v):
            if isinstance(v, (datetime.date, datetime.datetime)):
                return fields.Date.to_string(v)
            if isinstance(v, str) and len(v) >= 10 and v[4] == '-' and v[7] == '-':
                return v[:10]
            return v

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
                grid = []
                row_domain = []
                for f_idx, f in enumerate(row_fields[:level]):
                    row_domain.append((f, '=', row_key_list[f_idx]))
                
                for col in columns:
                    grid.append({
                        'value': 0,
                        'domain': expression.AND([domain, row_domain, col['domain']]),
                        'readonly': level < len(row_fields)
                    })

                rows_data[row_key] = {
                    'level': level,
                    'values': row_values,
                    'full_key': row_key_list,
                    'domain': row_domain,
                    'grid': grid,
                    'row_total': 0,
                    'is_leaf': level == len(row_fields)
                }
            
            # Match group to column
            # Prioritize Domain or __range for raw date
            c_val = None
            
            # 1. Check __range if it exists
            if '__range' in g:
                rng = g['__range']
                if isinstance(rng, str):
                    try: rng = json.loads(rng.replace("'", '"'))
                    except: rng = {}
                
                # Try all possible formats of the key
                for key in [col_field, f"{col_field}:{column_info['format']}"]:
                    if key in rng:
                        c_val = rng[key].get('from')
                        break

            # 2. Fallback: scan domain
            if not c_val:
                g_domain = g.get('__domain', [])
                for leaf in g_domain:
                    if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == col_field:
                        if leaf[1] in ('>=', '=', '>'):
                            c_val = leaf[2]
                            break
            
            if c_val:
                c_val_norm = normalize_date(c_val)
                matched = False
                for col_idx, col in enumerate(columns):
                    col_val_norm = normalize_date(col['values'][col_field])
                    if col_val_norm == c_val_norm:
                        val = g.get(cell_field, 0)
                        rows_data[row_key]['grid'][col_idx]['value'] = val
                        rows_data[row_key]['row_total'] += val
                        matched = True
                        break
                
                # Special case for step='week'/'month' etc where c_val might fall BETWEEN start and end
                if not matched and column_info['format'] != 'day':
                    # If it's a date, check if it fits in any column range
                    try:
                        c_date = fields.Date.from_string(c_val_norm)
                        for col_idx, col in enumerate(columns):
                            # Columns for ranges have domains like [('date', '>=', '...'), ('date', '<=', '...')]
                            # We can extract the start and end from col['domain']
                            c_start = None
                            c_end = None
                            for leaf in col['domain']:
                                if leaf[0] == col_field:
                                    if leaf[1] == '>=': c_start = fields.Date.from_string(leaf[2])
                                    if leaf[1] == '<=': c_end = fields.Date.from_string(leaf[2])
                            
                            if c_start and c_end and c_start <= c_date <= c_end:
                                val = g.get(cell_field, 0)
                                rows_data[row_key]['grid'][col_idx]['value'] = val
                                rows_data[row_key]['row_total'] += val
                                matched = True
                                break
                    except:
                        pass

        # 4. Totals Calculation
        col_totals = [0] * len(columns)
        grand_total = 0
        level_1_rows = [r for r in rows_data.values() if r['level'] == 1]
        for r in level_1_rows:
            for i, cell in enumerate(r['grid']):
                col_totals[i] += cell['value']
            grand_total += r['row_total']

        # Rounding
        for r in rows_data.values():
            r['row_total'] = round(r['row_total'], 10)
            for cell in r['grid']:
                cell['value'] = round(cell['value'], 10)
        col_totals = [round(v, 10) for v in col_totals]
        grand_total = round(grand_total, 10)

        # 5. Sorting
        rows_by_parent = {}
        for row in rows_data.values():
            parent_key = tuple(row['full_key'][:-1]) if row['level'] > 1 else ()
            if parent_key not in rows_by_parent:
                rows_by_parent[parent_key] = []
            rows_by_parent[parent_key].append(row)
        
        # Sort key logic
        sort_col_idx = None
        sort_order = 'asc'
        if orderby:
            parts = orderby.split(' ')
            sort_field = parts[0]
            sort_order = parts[1].lower() if len(parts) > 1 else 'asc'
            if ':' in sort_field:
                col_name, col_val = sort_field.split(':')
                for idx, col in enumerate(columns):
                    if col['values'].get(col_name) == col_val:
                        sort_col_idx = idx
                        break

        def sort_key(row):
            if sort_col_idx is not None:
                return row['grid'][sort_col_idx]['value']
            val = row['full_key'][row['level']-1]
            return val[1] if isinstance(val, tuple) else val
            
        reverse = (sort_order == 'desc')
        for p_key in rows_by_parent:
            rows_by_parent[p_key].sort(key=sort_key, reverse=reverse)
            
        sorted_rows = []
        def add_descendants(p_key):
            if p_key in rows_by_parent:
                for row in rows_by_parent[p_key]:
                    sorted_rows.append(row)
                    add_descendants(tuple(row['full_key']))
        
        add_descendants(())

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
        step = grid_range.get('step', 'day')
        anchor = grid_range.get('anchor')
        
        today = fields.Date.context_today(self)
        base_date = fields.Date.from_string(anchor) if anchor else today

        if span == 'week':
            start_date = base_date - datetime.timedelta(days=base_date.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif span == 'month':
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        elif span == 'quarter':
            quarter = (base_date.month - 1) // 3 + 1
            start_date = datetime.date(base_date.year, (quarter - 1) * 3 + 1, 1)
            end_date = start_date + relativedelta(months=3, days=-1)
        elif span == 'year':
            start_date = base_date.replace(month=1, day=1)
            end_date = start_date + relativedelta(years=1, days=-1)
        else:
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)

        columns = []
        if step == 'week':
            current_date = start_date - datetime.timedelta(days=start_date.weekday())
        elif step == 'month':
            current_date = start_date.replace(day=1)
        elif step == 'quarter':
            quarter = (start_date.month - 1) // 3 + 1
            current_date = datetime.date(start_date.year, (quarter - 1) * 3 + 1, 1)
        elif step == 'year':
            current_date = start_date.replace(month=1, day=1)
        else:
            current_date = start_date

        while current_date <= end_date:
            date_str = fields.Date.to_string(current_date)
            
            if step == 'week':
                next_date = current_date + datetime.timedelta(days=7)
                period_end = next_date - datetime.timedelta(days=1)
                col_start = max(current_date, start_date)
                col_end = min(period_end, end_date)
                label = f"{format_date(self.env, col_start)} - {format_date(self.env, col_end)}"
                columns.append({
                    'values': {name: date_str},
                    'domain': [(name, '>=', fields.Date.to_string(col_start)), (name, '<=', fields.Date.to_string(col_end))],
                    'is_current': today >= current_date and today <= period_end,
                    'label': label
                })
                current_date = next_date
            elif step == 'month':
                next_date = current_date + relativedelta(months=1)
                period_end = next_date - datetime.timedelta(days=1)
                col_start = max(current_date, start_date)
                col_end = min(period_end, end_date)
                if col_start != current_date or col_end != period_end:
                    label = f"{format_date(self.env, col_start)} - {format_date(self.env, col_end)}"
                else:
                    label = format_date(self.env, current_date, date_format='MMMM yyyy')
                columns.append({
                    'values': {name: date_str},
                    'domain': [(name, '>=', fields.Date.to_string(col_start)), (name, '<=', fields.Date.to_string(col_end))],
                    'is_current': today.month == current_date.month and today.year == current_date.year,
                    'label': label
                })
                current_date = next_date
            elif step == 'quarter':
                next_date = current_date + relativedelta(months=3)
                period_end = next_date - datetime.timedelta(days=1)
                col_start = max(current_date, start_date)
                col_end = min(period_end, end_date)
                if col_start != current_date or col_end != period_end:
                    label = f"{format_date(self.env, col_start)} - {format_date(self.env, col_end)}"
                else:
                    label = f"Q{(current_date.month - 1) // 3 + 1} {current_date.year}"
                columns.append({
                    'values': {name: date_str},
                    'domain': [(name, '>=', fields.Date.to_string(col_start)), (name, '<=', fields.Date.to_string(col_end))],
                    'is_current': today >= current_date and today <= period_end,
                    'label': label
                })
                current_date = next_date
            elif step == 'year':
                next_date = current_date + relativedelta(years=1)
                period_end = next_date - datetime.timedelta(days=1)
                col_start = max(current_date, start_date)
                col_end = min(period_end, end_date)
                if col_start != current_date or col_end != period_end:
                    label = f"{format_date(self.env, col_start)} - {format_date(self.env, col_end)}"
                else:
                    label = str(current_date.year)
                columns.append({
                    'values': {name: date_str},
                    'domain': [(name, '>=', fields.Date.to_string(col_start)), (name, '<=', fields.Date.to_string(col_end))],
                    'is_current': today.year == current_date.year,
                    'label': label
                })
                current_date = next_date
            else:
                columns.append({
                    'values': {name: date_str},
                    'domain': [(name, '=', date_str)],
                    'is_current': current_date == today,
                    'label': format_date(self.env, current_date)
                })
                current_date += datetime.timedelta(days=1)

        prev_date = start_date - datetime.timedelta(days=1)
        if span == 'week': prev_date = start_date - datetime.timedelta(days=7)
        elif span == 'month': prev_date = start_date - relativedelta(months=1)
        elif span == 'quarter': prev_date = start_date - relativedelta(months=3)
        elif span == 'year': prev_date = start_date - relativedelta(years=1)
        
        next_date = end_date + datetime.timedelta(days=1)
        if span == 'week': next_date = start_date + datetime.timedelta(days=7)
        elif span == 'month': next_date = start_date + relativedelta(months=1)
        elif span == 'quarter': next_date = start_date + relativedelta(months=3)
        elif span == 'year': next_date = start_date + relativedelta(years=1)
        
        return {
            'values': columns,
            'domain': [(name, '>=', fields.Date.to_string(start_date)), (name, '<=', fields.Date.to_string(end_date))],
            'format': step if step in ['day', 'week', 'month', 'quarter', 'year'] else 'day',
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
