# -*- coding: utf-8 -*-
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
    'version': '0.1',

    'depends': ['spreadsheet_dashboard', 'taz-common', 'project_accounting'],

    'data': [
        "data/dashboards.xml",
    ],
    'assets': {}
}
