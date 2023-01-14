{
    'name': "event_registrastion_light",

    'summary': """Light module to handle websiste event registration""",

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
    'depends': ['base', 'event', 'taz-common'],

    # always loaded
    'data': [
        'views/event_templates_page_light_registration.xml',
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
