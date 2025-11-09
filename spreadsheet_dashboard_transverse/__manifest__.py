{
    'name': "spreadsheet_dashboard_transverse",

    'summary': """Spreadsheet dashboard transverse""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': "18.0.1.0.0",

    'depends': ['spreadsheet_dashboard', 'taz-common', 'project_accounting', 'spreadsheet_filters', 'staffing'],

    'data': [
        "data/dashboards.xml",
    ],
    'assets': {}
}
