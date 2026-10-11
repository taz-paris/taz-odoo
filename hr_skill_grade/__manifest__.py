{
    'name': "hr_skill_grade",

    'summary': """Notes de compétences (auto-évaluation et évaluations tierces)""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'category': 'Uncategorized',
    'version': "18.0.1.0.0",

    'depends': ['hr_skills'],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_skill_views.xml',
        'views/hr_skill_level_views.xml',
        'views/hr_skill_type_views.xml',
        'views/hr_employee_skill_grade_views.xml',
        'views/hr_employee_skill_views.xml',
        'views/hr_employee_views.xml',
    ],
}
