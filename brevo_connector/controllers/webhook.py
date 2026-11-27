import hmac

from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


class BrevoWebhookController(http.Controller):

    @http.route(['/brevo/webhook/<string:token>'], type='http', auth="public", methods=['POST'], csrf=False, save_session=False)
    def brevo_webhook(self, token, **kwargs):
        """Webhook transactionnel Brevo (Transactionnel > Paramètres > Webhooks).

        Le jeton de l'URL doit être égal au paramètre système brevo_webhook_token : sinon l'appel est refusé (403).
        Une fois le jeton vérifié, on répond toujours 200, même en cas d'erreur de traitement : Brevo ne relance pas
        un appel qui a reçu une erreur, et l'événement est récupéré par le cron de rattrapage Brevo.
        """
        expected_token = request.env['ir.config_parameter'].sudo().get_param('brevo_webhook_token')
        if not expected_token or not hmac.compare_digest(token, expected_token):
            _logger.warning("Webhook Brevo : appel refusé (jeton invalide ou paramètre système brevo_webhook_token non valorisé)")
            return request.make_response("Forbidden", status=403)

        try:
            payload = request.get_json_data()
        except ValueError:
            _logger.warning("Webhook Brevo : contenu JSON illisible")
            return request.make_response("Bad Request", status=400)

        try:
            request.env['mailing.trace'].sudo()._brevo_process_webhook_payload(payload)
        except Exception:
            _logger.exception("Webhook Brevo : erreur lors du traitement de %s (récupéré par le cron de rattrapage Brevo)", payload)
            request.env.cr.rollback()
        return request.make_response("OK", status=200)
