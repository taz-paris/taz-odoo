{
    'name': "Web Grid View",
    'summary': "Web Grid view for odoo",
    'description': """
    
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'version': "18.0.1.0.0",
    'category': 'web',
    'depends': ['web'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'web_grid_view/static/src/js/**',
            'web_grid_view/static/src/xml/**',
            'web_grid_view/static/src/css/**',
        ],
    },
}
