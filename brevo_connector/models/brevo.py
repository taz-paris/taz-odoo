import requests

from odoo import _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

##################################################################
##########                SET PARAMETERS                ##########
##################################################################

BREVO_API_URL = "https://api.brevo.com/v3"
BREVO_API_TIMEOUT = 60
BREVO_API_PAGE_SIZE = 2500  # valeur par défaut de l'API Brevo pour /smtp/statistics/events


##################################################################
##########                 REST CLIENT                  ##########
##################################################################
class ClientRestBrevo:
    """Client minimaliste de l'API Brevo v3 (lecture seule).

    Documentation : https://developers.brevo.com/reference/get-email-event-report
    Authentification par clé API (en-tête `api-key`), stockée dans le paramètre système `brevo_api_key`.
    """

    def __init__(self, env):
        self.env = env
        self.API_KEY = self.env['ir.config_parameter'].sudo().get_param("brevo_api_key")
        if not self.API_KEY:
            raise ValidationError(_("Client API Brevo inactif car le paramètre système Odoo brevo_api_key n'est pas valorisé."))

    def get_transactional_events(self, event, start_date, end_date):
        """Renvoie (générateur) les événements transactionnels Brevo d'un type donné sur une période.

        :param event: type d'événement de l'API Brevo (hardBounces, softBounces, invalid, blocked, spam, unsubscribed)
        :param start_date, end_date: dates (date) incluses ; l'API refuse une période de plus de 90 jours
        """
        offset = 0
        while True:
            params = {
                'event': event,
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'limit': BREVO_API_PAGE_SIZE,
                'offset': offset,
                'sort': 'asc',
            }
            _logger.debug("API Brevo : lecture des événements %s du %s au %s (offset %s)", event, start_date, end_date, offset)
            try:
                response = requests.get(
                    BREVO_API_URL + "/smtp/statistics/events",
                    headers={'api-key': self.API_KEY, 'accept': 'application/json'},
                    params=params,
                    timeout=BREVO_API_TIMEOUT,
                )
            except requests.RequestException as e:
                raise ValidationError(_("Impossible de joindre l'API Brevo : %s", e))
            if response.status_code != 200:
                raise ValidationError(_("Erreur de l'API Brevo (HTTP %(status)s) : %(content)s", status=response.status_code, content=response.text[:500]))
            events = response.json().get('events') or []
            yield from events
            if len(events) < BREVO_API_PAGE_SIZE:
                break
            offset += BREVO_API_PAGE_SIZE
