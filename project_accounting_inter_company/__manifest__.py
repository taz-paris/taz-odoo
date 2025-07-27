# -*- coding: utf-8 -*-
{
    'name': "project_accounting_inter_company",

    'summary': """Project accounting inter-company""",

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

    # any module necessary for this one to work correctly
    'depends': ['project_accounting', 'account_invoice_inter_company', 'purchase_sale_inter_company'],

    # always loaded
    'data': [
        'views/project_outsourcing_link.xml',
        'views/account_move.xml',
        'views/purchase.xml',
        'views/sale.xml',
        'views/project.xml',
    ],
}
