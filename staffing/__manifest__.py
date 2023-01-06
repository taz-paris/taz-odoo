# -*- coding: utf-8 -*-
{
    'name': "staffing",

    'summary': """Staffing module""",

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
    'depends': ['base', 'project', 'hr', 'hr_holidays', 'hr_timesheet', 'project_timesheet_holidays', 'hr_skills', 'taz-common', 'web_widget_bokeh_chart'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/staffing.xml',
        'views/project.xml',
        'views/synchroFitnet.xml',
        'views/employee.xml',
        'views/account_analytic_line.xml',
        'views/hr_job.xml',
        'views/timesheets.xml',
        'views/res_partner.xml',
    ],


    #"assets": {
    #    "web.assets_backend": [
    #        "web_widget_bokeh_chart/static/src/js/web_widget_bokeh_chart.esm.js",
    #    ],
    #},

    #'assets': {
    #    'web.assets_backend': [
    #        'staffing/static/src/css/style.css',
    #    ],
    #}
}
