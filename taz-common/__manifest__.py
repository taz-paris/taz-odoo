# -*- coding: utf-8 -*-
{
    'name': "taz-common",

    'summary': """Module socle pour Tasmane""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],

    # always loaded
    'data': [
        'views/res_partner.xml',
        'views/business_action.xml',
        'security/ir.model.access.csv',
    ],
}
