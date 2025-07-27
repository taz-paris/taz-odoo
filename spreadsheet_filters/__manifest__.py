# -*- coding: utf-8 -*-
{
    'name': "spreadsheet_filters",

    'summary': """Spreadsheet filters""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '17.0',

    'depends': ['spreadsheet', 'spreadsheet_oca'],

    'data': [
    ],


    "assets": {
        'spreadsheet.o_spreadsheet': [
            "spreadsheet_filters/static/src/constants.js",
            "spreadsheet_filters/static/src/helpers.js",
        ],
    },
}
