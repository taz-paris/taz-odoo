# -*- coding: utf-8 -*-
{
    'name': "taz-common",

    'summary': """Module socle pour Tasmane""",

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

    # any module necessary for this one to work correctly
    'depends': ['base','mail', 'auth_oauth', 'web'],

    # always loaded
    'data': [
        'views/res_partner.xml',
        'views/business_action.xml',
        'views/office365_import_people.xml',
        'views/customer_book_goal.xml',
        'views/res_industry.xml',
        'views/res_users.xml',
        'views/contact_user_link.xml',
        'views/wizard_partner_category.xml',
        'security/ir.model.access.csv',
    ],
}
