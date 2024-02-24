# -*- coding: utf-8 -*-
{
    'name': "dashboard_global",

    'summary': """Classic dashboard - global perimeter""",

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

    'depends': ['board', 'taz-common', 'project_accounting'],

    'data': [
        "views/dashboards.xml",
        "views/outsourcing_dashboard.xml",
    ],
    'assets': {
        'web.assets_backend': [
             'dashboard_global/static/src/board_controller.js',
        ],
    },
}
