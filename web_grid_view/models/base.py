# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools import format_date
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
import datetime
import logging
import json

_logger = logging.getLogger(__name__)

class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_grid(self, row_fields, col_fields, cell_field, domain=None, grid_range=None, readonly_field=None, orderby=None, **kwargs):
        # Support legacy argument 'col_field'
        if 'col_field' in kwargs and not col_fields:
            col_fields = [kwargs['col_field']]
        if isinstance(col_fields, str):
            col_fields = [col_fields]
            
        domain = domain or []

        
        # Security: Filter out Falsey values and ensure Strings
        if not col_fields:
             col_fields = []
        col_fields = [f for f in col_fields if f and isinstance(f, str)]

        if not col_fields:
            # Fallback if no columns defined? Should error or return empty?
            # Let's handle it gracefully 
            return {'rows': [], 'cols': [], 'cols_tree': [], 'col_totals': [], 'grand_total': 0, 'prev': None, 'next': None}

        # 1. Generate Column Levels (Cartesian Product Preparation)
        # We will generate a list of lists: [ [ColLevel1_Values], [ColLevel2_Values] ]
        levels = []
        all_fields_to_fetch = list(set(col_fields + row_fields))
        fields_data = self.fields_get(all_fields_to_fetch, ['type', 'selection'])
        
        # Identify which field is the "Range/Step" field (usually the first Date/Datetime one)
        # We assume the grid_range config applies to the first Date field found, or defaults to the first field if none.
        try:
            range_field_name = next((f for f in col_fields if f in fields_data and fields_data[f]['type'] in ['date', 'datetime']), col_fields[0])
        except (IndexError, StopIteration):
             range_field_name = None
        
        column_info_map = {} # To store next/prev context from the Range field
        
        # Pre-calculate Range Info to apply time constraints to other columns
        if range_field_name and grid_range:
             column_info_map = self._grid_column_info(range_field_name, grid_range)

        # Prepare Discovery Domain (View Domain + Time Range)
        discovery_domain = domain
        if column_info_map.get('domain'):
             discovery_domain = expression.AND([domain, column_info_map['domain']])

        for field_name in col_fields:
            if field_name == range_field_name and grid_range:
                # Use the pre-calculated time-range values
                levels.append(column_info_map['values'])
            else:
                # For other fields, fetch distinct values present in the DISCOVERY domain
                # We interpret them as simple categorical columns
                groups = self.read_group(discovery_domain, [field_name], [field_name], lazy=False)
                
                level_cols = []
                seen = set()
                for g in groups:
                    val = g[field_name]
                    # val can be (id, name) for many2one, or raw value
                    raw_val = val[0] if isinstance(val, tuple) else val
                    label_val = val[1] if isinstance(val, tuple) else str(val)
                    
                    if field_name in fields_data and fields_data[field_name]['type'] == 'selection':
                        sel = fields_data[field_name].get('selection')
                        if sel and isinstance(sel, list):
                             for k, v in sel:
                                 if k == raw_val:
                                     label_val = v
                                     break
                    
                    if raw_val not in seen:
                        seen.add(raw_val)
                        level_cols.append({
                            'values': {field_name: raw_val},
                            'domain': [(field_name, '=', raw_val)],
                            'label': label_val,
                            'is_current': False
                        })
                # If no data found for this category, maybe we shouldn't show it? 
                # Or should we show an "Undefined" column? 
                # For now let's rely on read_group.
                levels.append(level_cols)

        # 2. Build Cartesian Product of Columns (Tree & Leaves)
        # We need a recursive function to build the tree
        def build_tree(depth, current_values, current_domain, current_labels):
            if depth == len(levels):
                return [], [{
                    'values': current_values,
                    'domain': expression.AND(current_domain),
                    'labels': current_labels
                }]

            current_level_cols = levels[depth]
            nodes = []
            leaves = []
            
            for col in current_level_cols:
                # Merge values
                new_values = {**current_values, **col['values']}
                new_domain = current_domain + [col['domain']]
                new_labels = current_labels + [col['label']]
                
                children_nodes, children_leaves = build_tree(depth + 1, new_values, new_domain, new_labels)
                
                start_node = {
                    'label': col['label'],
                    'values': col['values'],
                    'domain': col['domain'],
                    'is_current': col.get('is_current', False),
                    'children': children_nodes
                }
                nodes.append(start_node)
                leaves.extend(children_leaves)
                
            return nodes, leaves

        root_nodes, leaf_columns = build_tree(0, {}, [domain], [])

        # 3. Fetch Data
        groupby = []
        for f in row_fields:
            groupby.append(f)

        # Determine temporal format if applicable
        temporal_format = None
        if range_field_name and 'format' in column_info_map:
            temporal_format = column_info_map['format']

        # Track Group Keys map
        col_group_keys = {}
        for f in col_fields:
            if f == range_field_name and temporal_format:
                key = f"{f}:{temporal_format}"
                groupby.append(key)
                col_group_keys[f] = key
            else:
                groupby.append(f)
                col_group_keys[f] = f

        fetch_domain = domain
        if 'domain' in column_info_map:
            # Safely merge domains
            if fetch_domain and column_info_map['domain']:
                fetch_domain = expression.AND([fetch_domain, column_info_map['domain']])
            elif column_info_map['domain']:
                fetch_domain = column_info_map['domain']

        current_orderby = None
        if orderby:
            parts = orderby.split(' ')
            sort_field = parts[0]
            sort_order = parts[1] if len(parts) > 1 else 'asc'
            if sort_field in row_fields:
                current_orderby = f"{sort_field} {sort_order}"

        # 4. Process Groups into Rows Data
        row_levels_data = {}

        def normalize_date(v):
            if isinstance(v, (datetime.date, datetime.datetime)):
                return fields.Date.to_string(v)
            if isinstance(v, str) and len(v) >= 10 and v[4] == '-' and v[7] == '-':
                return v[:10]
            return v
        


        # Single Pass Loop over Row Levels
        for i in range(1, len(row_fields) + 1):
            current_row_fields = row_fields[:i]
            level_groupby = current_row_fields + groupby[len(row_fields):]
            
            level_groups = self.read_group(fetch_domain, [cell_field], level_groupby, lazy=False, orderby=current_orderby)
            
            for g in level_groups:
                # Construct Row Key
                key_elements = []
                r_values_map = {}
                for f in current_row_fields:
                     val = g[f]
                     if isinstance(val, tuple):
                         key_elements.append(val[0])
                         r_values_map[f] = val[1]
                     else:
                         key_elements.append(val)
                         # Try to resolve selection label
                         label = val
                         if f in fields_data and fields_data[f]['type'] == 'selection':
                             sel = fields_data[f].get('selection')
                             if sel and isinstance(sel, list):
                                 for k, v in sel:
                                     if k == val:
                                         label = v
                                         break
                         r_values_map[f] = label
                r_key = tuple(key_elements)
                
                # Init Row if needed
                if (i, r_key) not in row_levels_data:
                    # Init Grid
                    grid = []
                    row_domain = [(f, '=', key_elements[idx]) for idx, f in enumerate(current_row_fields)]
                    
                    # Evaluate ROW field readonly expressions
                    readonly_exprs = kwargs.get('readonly_field_exprs', {})
                    is_row_readonly = False
                    
                    # Context for safe_eval: Use the group data 'g' which has values like {category: 'project_forecast'}
                    # We might need to handle tuple values (many2one) by providing both id and name?
                    # For now, simple values from 'g' usually sufficient.
                    eval_context = {k: (v[0] if isinstance(v, tuple) else v) for k, v in g.items()}
                    
                    for f in current_row_fields:
                        expr = readonly_exprs.get(f)
                        if expr:
                            try:
                                # Check for simple true/1 boolean flags (legacy/static support)
                                if str(expr).lower() in ['1', 'true']:
                                    is_row_readonly = True
                                else:
                                    if safe_eval(expr, eval_context):
                                        is_row_readonly = True
                            except:
                                # On error, assume not readonly or log warning?
                                pass

                    for col in leaf_columns:
                         # Combine domains
                         full_domain = expression.AND([domain, row_domain, col['domain']])
                         
                         is_col_readonly = False
                         for f in col['values'].keys():
                             expr = readonly_exprs.get(f)
                             if expr:
                                 # We need to update context with COLUMN values for this specific column
                                 col_context = eval_context.copy()
                                 col_context.update(col['values'])
                                 
                                 try:
                                     if str(expr).lower() in ['1', 'true']:
                                          is_col_readonly = True
                                     elif safe_eval(expr, col_context):
                                          is_col_readonly = True
                                 except:
                                     pass
                         
                         grid.append({
                             'value': 0, 
                             'readonly': (i < len(row_fields)) or is_row_readonly or is_col_readonly, 
                             'domain': full_domain
                         })

                    row_levels_data[(i, r_key)] = {
                        'level': i,
                        'values': r_values_map,
                        'full_key': list(r_key),
                        'grid': grid,
                        'row_total': 0,
                        'is_leaf': i == len(row_fields),
                        'domain': row_domain,
                    }

                # Find Col Index
                col_idx = -1
                for idx, col in enumerate(leaf_columns):
                    match = True
                    for field in col_fields:
                        # Use correct group key
                        group_key = col_group_keys.get(field, field)
                        g_val = g.get(group_key)
                        
                        if isinstance(g_val, tuple): g_val = g_val[0]
                        c_val = col['values'].get(field)
                        
                        is_date = field in fields_data and fields_data[field]['type'] in ['date', 'datetime']
                        
                        if is_date:
                             g_val_norm = normalize_date(g_val)
                             # 1. Exact Value Match (Normalized)
                             if g_val_norm == c_val:
                                  continue
                             
                             # 2. Label Match
                             if str(g_val) == col.get('label'):
                                  continue 

                             # 3. Explicit Range Meta Check (Robust)
                             # Compare Group Start Date (from __domain) with Column Range
                             col_range = col['values'].get(f"{field}__range")
                             if col_range:
                                 # We have an explicit range for the column
                                 c_start_iso, c_end_iso = col_range
                                 
                                 # We need the Group Start date
                                 g_domain = g.get('__domain', [])
                                 g_start_iso = None
                                 
                                 # Extract Start Date from Group Domain
                                 for leaf in g_domain:
                                     if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == field:
                                         if leaf[1] in ['>=', '=']:
                                              g_start_iso = leaf[2]
                                              break
                                 
                                 # If we didn't find it in domain (e.g. format='day' often returns exact val),
                                 # try the normalized value if it looks like ISO
                                 if not g_start_iso and isinstance(g_val_norm, str) and len(g_val_norm) == 10 and g_val_norm[4] == '-':
                                      g_start_iso = g_val_norm

                                 if g_start_iso and c_start_iso and c_end_iso:
                                      if c_start_iso <= g_start_iso <= c_end_iso:
                                           continue
                                           
                             # 4. Range Check on Normalized Value (Legacy Fallback)
                             is_match_range = False
                             c_end = None
                             for leaf in col['domain']:
                                 if isinstance(leaf, (list, tuple)) and leaf[0] == field:
                                     if leaf[1] == '<=': c_end = leaf[2]
                                     elif leaf[1] == '=': c_end = leaf[2]
                             
                             is_valid_date_str = isinstance(g_val_norm, str) and len(g_val_norm) >= 10 and g_val_norm[4] == '-'
                             
                             if is_valid_date_str and c_start and c_end and c_start <= g_val_norm <= c_end:
                                  is_match_range = True
                             
                             if not is_match_range:
                                  # log_debug(f"MISMATCH: F={field} G={g_val} GValNorm={g_val_norm} CRange={col_range}")
                                  match = False; break
                        else:
                            if g_val != c_val:
                                match = False; break
                    
                    if match:
                        col_idx = idx
                        break
                
                if col_idx >= 0:
                     val = g.get(cell_field, 0)
                     if col_idx < len(row_levels_data[(i, r_key)]['grid']):
                         row_levels_data[(i, r_key)]['grid'][col_idx]['value'] += val
                         row_levels_data[(i, r_key)]['row_total'] += val
                else:
                     pass

        # 5. Sorting & Finalizing
        final_rows = list(row_levels_data.values())
        
        # Calculate Column Totals
        col_totals = [0] * len(leaf_columns)
        for r in final_rows:
            if r['level'] == 1:
                for i, cell in enumerate(r['grid']):
                    col_totals[i] += cell['value']

        return {
            'rows': final_rows,
            'cols': leaf_columns, 
            'cols_tree': root_nodes, 
            'col_totals': col_totals,
            'grand_total': sum(col_totals),
            'prev': column_info_map.get('prev'),
            'next': column_info_map.get('next'),
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
            label = ""
            col_start = current_date
            col_end = current_date
            
            if step == 'week':
                next_date = current_date + datetime.timedelta(days=7)
                period_end = next_date - datetime.timedelta(days=1)
                col_start = max(current_date, start_date)
                col_end = min(period_end, end_date)
                label = f"{format_date(self.env, col_start)} - {format_date(self.env, col_end)}"
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
                current_date = next_date
            else:
                # Day step
                col_start = current_date
                col_end = current_date
                label = format_date(self.env, current_date)
                current_date += datetime.timedelta(days=1)
            
            columns.append({
                'values': {
                    name: date_str,
                    f"{name}__range": (fields.Date.to_string(col_start), fields.Date.to_string(col_end))
                },
                'domain': [(name, '>=', fields.Date.to_string(col_start)), (name, '<=', fields.Date.to_string(col_end))],
                'is_current': today >= col_start and today <= col_end,
                'label': label
            })

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
            'format': 'day', # Force daily granularity for robust matching
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
