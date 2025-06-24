{
    'name': "napta_connector",

    'summary': """Connector for exchanging data with Napta""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'category': 'Uncategorized',
    'version': '17.0',

    'depends': ['staffing', 'project_accounting', 'project', 'analytic'],

    'data': [
        'security/ir.model.access.csv',
        'data/cron_sync.xml',
        'views/project.xml',
        'views/napta.xml',
        'views/wizard_timesheet_mass_validation.xml',
    ],

}
