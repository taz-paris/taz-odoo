{
    'name': "Web Grid View",
    'summary': "A powerful, flexible, and hierarchical grid view for Odoo 18.",
    'description': """
The Web Grid View allows users to visualize and edit data in a matrix format, 
similar to a spreadsheet but integrated with Odoo's business objects.

### 1. Basic XML Structure
```xml
<grid string="My Grid" adjustment="object" adjust_name="adjust_grid_method">
    <field name="project_id" type="row"/>
    <field name="employee_id" type="row">
        <step_decorator step="step_day" decoration-danger="unit_amount > 8" decoration-success="unit_amount == 7"/>
    </field>

    <field name="date" type="col">
        <range name="span_month" string="Month" span="month"/>
        <range name="span_week" string="Week" span="week"/>

        <step name="step_day" string="Day" step="day"/>
        <step name="step_month" string="Month" step="month"/>
    </field>

    <field name="unit_amount" type="measure" widget="float_time"/>
</grid>
```

### 2. Main Attributes (<grid/>)
- `create_inline`: (Boolean) If true, allows adding new lines directly in the grid interface.
- `adjustment`: Set to "object" to trigger a server-side Python method when a cell is edited.
- `adjust_name`: The name of the Python method to call (must be defined on the model).
- `display_empty`: Show the grid even if no data is found for the period.
- `hide_line_total`: Hide the total column on the right.
- `hide_column_total`: Hide the total row at the bottom.

### 3. Fields
- `type="row"`: Defines grouped rows. Priority follows the order of fields in the XML or the 'Group By' from the search bar.
- `type="col"`: Defines the horizontal axis (usually a Date/Datetime field).
- `type="measure"`: The value to display in cells.

### 4. Spans & Steps (under col field)
- `<range/>`: Defines the time period displayed (span: 'week', 'month', 'quarter', 'year').
- `<step/>`: Defines the columns granularity (step: 'day', 'week', 'month', 'year').

### 5. Advanced Decorations
Decorations can be defined at multiple levels (Field, Range, Step, Row). The engine uses the most specific rule.
- **Context Variables**: Expressions can access:
    - `value` or `[measure_field_name]`: Current cell value.
    - `__depth`: Current row grouping depth (0-indexed).
    - `__is_leaf`: True if it's the last grouping level.
    - `[field_name]`: Any data field from the row (for many2one, it provides the ID).

- **Row-Aware Decorations**: 
  Use `<step_decorator/>` inside a row field to apply colors specifically to that level:
  ```xml
  <field name="employee_id" type="row">
      <step_decorator step="step_day" decoration-danger="unit_amount > 8"/>
  </field>
  ```
  This rule will reference the global `step` with the name "step_day" but only color rows grouped by "Employee".

### 6. Action Context
You can pre-configure the grid view from an action context using:
- `grid_range`: The name of a `<range/>` tag.
- `grid_step`: The name of a `<step/>` tag.
- `grid_anchor`: A default date string (YYYY-MM-DD).
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'version': "18.0.1.1.0",
    'category': 'web',
    'depends': ['web'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'web_grid_view/static/src/js/**',
            'web_grid_view/static/src/xml/**',
            'web_grid_view/static/src/css/**',
        ],
    },
}
