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
    'version': "18.0.1.0.0",

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'hr', 'hr_holidays', 'hr_timesheet', 'hr_contract', 'project_timesheet_holidays', 'hr_skills', 'taz-common', 'project_accounting', 'web_widget_bokeh_chart', 'web_grid_view'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/staffing.xml',
        'views/project.xml',
        'views/employee.xml',
        'views/account_analytic_line.xml',
        'views/hr_job.xml',
        'views/res_company.xml',
        'views/timesheets.xml',
        'views/hr_contract.xml',
        'views/employee_staffing_report.xml',
        'views/timesheet_grid.xml',
        'views/napta_shell_menus.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'staffing/static/src/napta_shell/menu_config.js',
            'staffing/static/src/napta_shell/components/assignment_drawer/assignment_drawer.js',
            'staffing/static/src/napta_shell/components/assignment_drawer/assignment_drawer.xml',
            'staffing/static/src/napta_shell/pages/staffing_projects/staffing_projects.js',
            'staffing/static/src/napta_shell/pages/staffing_projects/staffing_projects.xml',
            'staffing/static/src/napta_shell/pages/staffing_requests/staffing_requests.js',
            'staffing/static/src/napta_shell/pages/staffing_requests/staffing_requests.xml',
            'staffing/static/src/napta_shell/pages/staffing_modification_requests/staffing_modification_requests.js',
            'staffing/static/src/napta_shell/pages/staffing_modification_requests/staffing_modification_requests.xml',
            'staffing/static/src/napta_shell/pages/staffing_staffings/staffing_staffings.js',
            'staffing/static/src/napta_shell/pages/staffing_staffings/staffing_staffings.xml',
            'staffing/static/src/napta_shell/pages/staffing_global_calendar/staffing_global_calendar.js',
            'staffing/static/src/napta_shell/pages/staffing_global_calendar/staffing_global_calendar.xml',
            'staffing/static/src/napta_shell/pages/timesheets_timesheet/timesheets_timesheet.js',
            'staffing/static/src/napta_shell/pages/timesheets_timesheet/timesheets_timesheet.xml',
            'staffing/static/src/napta_shell/pages/evaluations_mission/evaluations_mission.js',
            'staffing/static/src/napta_shell/pages/evaluations_mission/evaluations_mission.xml',
            'staffing/static/src/napta_shell/pages/reports_occupation_globale/reports_occupation_globale.js',
            'staffing/static/src/napta_shell/pages/reports_occupation_globale/reports_occupation_globale.xml',
            'staffing/static/src/napta_shell/pages/reports_planification_individuelle/reports_planification_individuelle.js',
            'staffing/static/src/napta_shell/pages/reports_planification_individuelle/reports_planification_individuelle.xml',
            'staffing/static/src/napta_shell/pages/reports_availability_hub/reports_availability_hub.js',
            'staffing/static/src/napta_shell/pages/reports_availability_hub/reports_availability_hub.xml',
            'staffing/static/src/napta_shell/pages/reports_suivi_charge/reports_suivi_charge.js',
            'staffing/static/src/napta_shell/pages/reports_suivi_charge/reports_suivi_charge.xml',
            'staffing/static/src/napta_shell/pages/reports_suivi_consomme/reports_suivi_consomme.js',
            'staffing/static/src/napta_shell/pages/reports_suivi_consomme/reports_suivi_consomme.xml',
            'staffing/static/src/napta_shell/pages/reports_suivi_financier_global/reports_suivi_financier_global.js',
            'staffing/static/src/napta_shell/pages/reports_suivi_financier_global/reports_suivi_financier_global.xml',
            'staffing/static/src/napta_shell/pages/reports_competences_globales/reports_competences_globales.js',
            'staffing/static/src/napta_shell/pages/reports_competences_globales/reports_competences_globales.xml',
            'staffing/static/src/napta_shell/pages/reports_competences_individuelles/reports_competences_individuelles.js',
            'staffing/static/src/napta_shell/pages/reports_competences_individuelles/reports_competences_individuelles.xml',
            'staffing/static/src/napta_shell/pages/registry.js',
            'staffing/static/src/napta_shell/napta_shell.js',
            'staffing/static/src/napta_shell/napta_shell.xml',
            'staffing/static/src/napta_shell/napta_shell.scss',
            'staffing/static/src/napta_shell/components/assignment_drawer/assignment_drawer.scss',
            'staffing/static/src/napta_shell/pages/staffing_projects/staffing_projects.scss',
            'staffing/static/src/napta_shell/pages/staffing_requests/staffing_requests.scss',
            'staffing/static/src/napta_shell/pages/staffing_modification_requests/staffing_modification_requests.scss',
            'staffing/static/src/napta_shell/pages/staffing_staffings/staffing_staffings.scss',
            'staffing/static/src/napta_shell/pages/staffing_global_calendar/staffing_global_calendar.scss',
            'staffing/static/src/napta_shell/pages/timesheets_timesheet/timesheets_timesheet.scss',
            'staffing/static/src/napta_shell/pages/evaluations_mission/evaluations_mission.scss',
            'staffing/static/src/napta_shell/pages/reports_occupation_globale/reports_occupation_globale.scss',
            'staffing/static/src/napta_shell/pages/reports_planification_individuelle/reports_planification_individuelle.scss',
            'staffing/static/src/napta_shell/pages/reports_availability_hub/reports_availability_hub.scss',
            'staffing/static/src/napta_shell/pages/reports_suivi_charge/reports_suivi_charge.scss',
            'staffing/static/src/napta_shell/pages/reports_suivi_consomme/reports_suivi_consomme.scss',
            'staffing/static/src/napta_shell/pages/reports_suivi_financier_global/reports_suivi_financier_global.scss',
            'staffing/static/src/napta_shell/pages/reports_competences_globales/reports_competences_globales.scss',
            'staffing/static/src/napta_shell/pages/reports_competences_individuelles/reports_competences_individuelles.scss',
        ],
    },

}
