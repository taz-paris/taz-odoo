{
    'name': "project_evaluation",

    'summary': """Évaluations de mission et leurs gabarits""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'category': 'Uncategorized',
    'version': "18.0.1.0.0",

    'depends': ['project', 'hr'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/project_evaluation_template_views.xml',
        'views/project_evaluation_views.xml',
        'views/project_evaluation_menus.xml',
    ],
}
