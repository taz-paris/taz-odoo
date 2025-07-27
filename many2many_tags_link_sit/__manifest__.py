
{
    'name': ' Many2Many Tags Link',
    'version': '17.0',
    'category': '',
    'summary': ' Many2Many Tags Link.',
    'description': """The Many2Many Tag Links module for Odoo is a feature-enhancing extension that addresses the limitation of non-clickable many-to-many tag widgets in the Odoo system. """,
    'author': 'Silent Infotech Pvt. Ltd., Aurélien Dumaine',
    'category': 'Tools',
    'license': u'OPL-1',
    'price': 0.00,
    'currency': 'USD',
    'website': 'https://silentinfotech.com',

    'depends': ['base', 'web'],
    "images": ['static/description/banner.gif'],
    'assets': {
        'web.assets_backend': [
            'many2many_tags_link_sit/static/src/js/many2many_tags_field.js',
        ],

    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
