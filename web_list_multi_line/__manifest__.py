{
    'name': 'Web List Multi-line View',
    'version': '18.0.1.0.0',
    'category': 'Web',
    'summary': 'A list view where records are displayed as multi-line rows (form-like structure).',
    'author': 'Antigravity',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'web_list_multi_line/static/src/js/**/*.js',
            'web_list_multi_line/static/src/xml/**/*.xml',
            'web_list_multi_line/static/src/css/**/*.css',
        ],
    },
    'installable': True,
    'auto_install': False,
}
