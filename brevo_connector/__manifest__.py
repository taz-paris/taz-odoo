{
    'name': "brevo_connector",
    'summary': """Connector for receiving email events (bounces, spam, unsubscriptions) from Brevo""",
    'description': """
Connecteur Brevo (relais SMTP utilisé pour les campagnes Email Marketing).
Le connecteur ne fait que recevoir des données depuis Brevo, il n'en envoie jamais.

 - webhook POST /brevo/webhook/<jeton> : reçoit en temps réel les événements hard_bounce, soft_bounce, invalid_email, blocked, spam et unsubscribed (webhook transactionnel Brevo)
 - bounces : traités avec la logique standard d'Odoo (trace de mailing en « Rebondi », compteur de bounces des contacts, liste noire automatique après 5 bounces espacés)
 - hard bounce, email invalide, adresse bloquée, plainte spam, désinscription : liste noire immédiate
 - cron journalier : relit via l'API Brevo les événements des 3 derniers jours, pour rattraper ceux que le webhook n'a pas reçus (Brevo ne relance pas un webhook qui a reçu une erreur 5xx, par exemple quand TazForce est arrêté)
 - assistant « Rattrapage Brevo » : même rattrapage sur les N derniers jours (90 max), pour une panne plus longue ou la reprise d'historique

Paramètres système : brevo_webhook_token et brevo_api_key (effacés à la neutralisation de la base).
    """,
    'author': "Florentin Michaud",
    'website': "",
    'license': 'LGPL-3',
    'category': 'Marketing/Email Marketing',
    'version': "18.0.1.0.0",
    'depends': ['mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_sync.xml',
        'views/wizard_brevo_catchup.xml',
    ],
}
