{
    'name': "lucca_connector",

    'summary': """Connector for importing data from Lucca (API v5)""",

    'description': """
Connecteur Lucca (API v5 : https://developers.luccasoftware.com/documentation/get-started/introduction).

Le connecteur ne fait que recevoir des données depuis Lucca, il n'en envoie jamais.

Pour le moment :
 - ajoute un identifiant Lucca (lucca_id, lecture seule) sur hr.employee et hr.leave
 - l'affiche dans les formulaires de ces deux objets
    """,

    'author': "Aurélien Dumaine",
    'website': "https://www.dumaine.me",
    'license': 'LGPL-3',

    'category': 'Human Resources',
    'version': "18.0.1.0.0",

    'depends': ['hr', 'hr_holidays'],

    'data': [
        'views/hr_employee_views.xml',
        'views/hr_leave_views.xml',
    ],
}
