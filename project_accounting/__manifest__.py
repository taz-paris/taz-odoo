# -*- coding: utf-8 -*-
{
    'name': "project_accounting",

    'summary': """Project accounting""",

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
    'depends': ['base', 'account', 'project', 'analytic', 'sale', 'taz-common', 'sale_management', 'web_widget_bokeh_chart'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/project_stage.xml',
        'views/project_group.xml',
        'data/project_data.xml',
        'views/project.xml',
        'views/res_partner.xml',
        'views/project_outsourcing_link.xml',
        'views/project_book.xml',
        'views/report_invoice.xml',
        'views/sale_order.xml',
        'views/res_company.xml',
        'views/purchase_order.xml',
        'views/project_accounting_closing.xml',
        'views/payment.xml',
        'views/account_move.xml',
        'views/wizard_accounting_closing_mass_creation.xml',
        'views/employee_book_goal.xml',
    ],


    "assets": {
        "web.assets_backend": [
            "project_accounting/static/src/analytic_distribution_project_access.xml",
            "project_accounting/static/src/analytic_distribution_project_access.js",
        ],
    },
}
