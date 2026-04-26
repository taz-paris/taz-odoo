{
    'name': "napta_connector",

    'summary': """Connector for exchanging data with Napta""",

    'description': """
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'category': 'Uncategorized',
    'version': "18.0.1.0.0",

    'depends': ['staffing', 'project_accounting', 'project', 'analytic'],

    'data': [
        'security/ir.model.access.csv',
        'data/cron_sync.xml',
        'data/project_stage_data.xml',
        'views/napta.xml',
        'views/project.xml',
        'views/wizard_timesheet_mass_validation.xml',
    ],

}
