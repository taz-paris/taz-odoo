import json
from unittest import mock

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged


class BrevoConnectorCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': "Contact test Brevo", 'email': "Contact.Brevo@Example.com"})
        cls.mailing = cls.env['mailing.mailing'].create({
            'subject': "Campagne test Brevo",
            'body_html': "<p>Bonjour</p>",
            'mailing_model_id': cls.env.ref('base.model_res_partner').id,
        })
        cls.trace = cls._make_trace("<brevo-test-1@odoo.example.com>")

    @classmethod
    def _make_trace(cls, message_id, partner=None, sent_datetime=None):
        partner = partner or cls.partner
        return cls.env['mailing.trace'].create({
            'trace_type': 'mail',
            'mass_mailing_id': cls.mailing.id,
            'model': 'res.partner',
            'res_id': partner.id,
            'email': partner.email_normalized,
            'message_id': message_id,
            'trace_status': 'sent',
            'sent_datetime': sent_datetime or fields.Datetime.now(),
        })

    def _is_blacklisted(self, email="contact.brevo@example.com"):
        return bool(self.env['mail.blacklist'].search([('email', '=', email)]))


@tagged("post_install", "-at_install")
class TestBrevoEvents(BrevoConnectorCommon):

    def test_hard_bounce(self):
        """Hard bounce : envoi en « Rebondi » avec la raison, compteur +1, liste noire immédiate."""
        result = self.env['mailing.trace']._brevo_process_event(
            'hard_bounce', "contact.brevo@example.com", message_id="brevo-test-1@odoo.example.com", reason="550 user unknown")
        self.assertEqual(result, 'processed')
        self.assertEqual(self.trace.trace_status, 'bounce')
        self.assertEqual(self.trace.failure_type, 'mail_bounce')
        self.assertIn("550 user unknown", self.trace.failure_reason)
        self.assertEqual(self.partner.message_bounce, 1)
        self.assertTrue(self._is_blacklisted())

    def test_soft_bounce(self):
        """Soft bounce : envoi en « Rebondi » et compteur +1, mais pas de liste noire (règle standard Odoo)."""
        result = self.env['mailing.trace']._brevo_process_event(
            'soft_bounce', "contact.brevo@example.com", message_id="<brevo-test-1@odoo.example.com>", reason="mailbox full")
        self.assertEqual(result, 'processed')
        self.assertEqual(self.trace.trace_status, 'bounce')
        self.assertEqual(self.partner.message_bounce, 1)
        self.assertFalse(self._is_blacklisted())

    def test_duplicate_event_is_ignored(self):
        """Un même événement reçu deux fois (webhook rejoué, rattrapage) n'est compté qu'une fois."""
        Trace = self.env['mailing.trace']
        Trace._brevo_process_event('soft_bounce', "contact.brevo@example.com", message_id="brevo-test-1@odoo.example.com")
        result = Trace._brevo_process_event('soft_bounce', "contact.brevo@example.com", message_id="brevo-test-1@odoo.example.com")
        self.assertEqual(result, 'ignored')
        self.assertEqual(self.partner.message_bounce, 1)

    def test_fallback_on_email_without_message_id(self):
        """Sans Message-ID exploitable, l'événement est rattaché au dernier envoi à cette adresse."""
        result = self.env['mailing.trace']._brevo_process_event(
            'soft_bounce', "CONTACT.BREVO@example.com", message_id="<inconnu@smtp-relay.brevo.com>")
        self.assertEqual(result, 'processed')
        self.assertEqual(self.trace.trace_status, 'bounce')

    def test_fallback_ignores_old_sendings(self):
        """Un envoi de plus de 30 jours n'est pas rattaché à un bounce sans Message-ID."""
        self.trace.sent_datetime = fields.Datetime.subtract(fields.Datetime.now(), days=45)
        result = self.env['mailing.trace']._brevo_process_event('soft_bounce', "contact.brevo@example.com")
        self.assertEqual(result, 'not_found')
        self.assertEqual(self.trace.trace_status, 'sent')

    def test_spam_and_unsubscribed_blacklist_only(self):
        """Spam et désinscription : liste noire, sans toucher à l'envoi ni au compteur de bounces."""
        Trace = self.env['mailing.trace']
        self.assertEqual(Trace._brevo_process_event('spam', "contact.brevo@example.com"), 'processed')
        self.assertTrue(self._is_blacklisted())
        self.assertEqual(self.trace.trace_status, 'sent')
        self.assertEqual(self.partner.message_bounce, 0)
        # déjà en liste noire : rien de plus à faire
        self.assertEqual(Trace._brevo_process_event('unsubscribed', "contact.brevo@example.com"), 'ignored')

    def test_unknown_email(self):
        """Un bounce sur une adresse jamais contactée ne plante pas ; un hard bounce la met quand même en liste noire."""
        Trace = self.env['mailing.trace']
        self.assertEqual(Trace._brevo_process_event('soft_bounce', "inconnu@example.com"), 'not_found')
        self.assertFalse(self._is_blacklisted("inconnu@example.com"))
        self.assertEqual(Trace._brevo_process_event('hard_bounce', "inconnu@example.com"), 'processed')
        self.assertTrue(self._is_blacklisted("inconnu@example.com"))

    def test_invalid_input_is_ignored(self):
        Trace = self.env['mailing.trace']
        self.assertEqual(Trace._brevo_process_event('hard_bounce', "pas-une-adresse"), 'ignored')
        self.assertEqual(Trace._brevo_process_event('opened', "contact.brevo@example.com"), 'ignored')

    def test_webhook_payload_list(self):
        """Le webhook accepte un événement seul ou une liste (envoi groupé), et ignore les autres événements."""
        self.env['mailing.trace']._brevo_process_webhook_payload([
            {'event': 'delivered', 'email': "contact.brevo@example.com"},
            {'event': 'hard_bounce', 'email': "contact.brevo@example.com",
             'message-id': "<brevo-test-1@odoo.example.com>", 'reason': "550", 'ts_event': 1795784400},
        ])
        self.assertEqual(self.trace.trace_status, 'bounce')
        self.assertTrue(self._is_blacklisted())

    def test_parse_date(self):
        Trace = self.env['mailing.trace']
        self.assertEqual(str(Trace._brevo_parse_date("2026-11-27T14:00:00.000+01:00")), "2026-11-27 13:00:00")
        self.assertEqual(str(Trace._brevo_parse_date("2026-11-27 14:00:00")), "2026-11-27 14:00:00")
        self.assertEqual(str(Trace._brevo_parse_date(1795784400)), "2026-11-27 13:00:00")
        self.assertFalse(Trace._brevo_parse_date(False))
        self.assertFalse(Trace._brevo_parse_date("n'importe quoi"))


@tagged("post_install", "-at_install")
class TestBrevoCatchup(BrevoConnectorCommon):

    def _mock_response(self, events):
        response = mock.Mock(status_code=200)
        response.json.return_value = {'events': events}
        return response

    def test_catchup_requires_api_key(self):
        self.env['ir.config_parameter'].sudo().set_param('brevo_api_key', False)
        with self.assertRaises(ValidationError):
            self.env['mailing.trace']._brevo_catchup(7)

    def test_catchup_limits(self):
        with self.assertRaises(ValidationError):
            self.env['wizard_brevo_catchup'].create({'days': 91})

    def test_catchup(self):
        """Le rattrapage interroge l'API pour chaque type d'événement et applique la même logique que le webhook."""
        self.env['ir.config_parameter'].sudo().set_param('brevo_api_key', "cle-de-test")

        def fake_get(url, headers=None, params=None, timeout=None):
            self.assertEqual(headers['api-key'], "cle-de-test")
            if params['event'] == 'hardBounces':
                return self._mock_response([{
                    'email': "contact.brevo@example.com", 'messageId': "<brevo-test-1@odoo.example.com>",
                    'date': "2026-11-27T14:00:00.000+01:00", 'reason': "550 user unknown"}])
            if params['event'] == 'spam':
                return self._mock_response([{'email': "contact.brevo@example.com", 'date': "2026-11-27T15:00:00.000+01:00"}])
            return self._mock_response([])

        with mock.patch('odoo.addons.brevo_connector.models.brevo.requests.get', side_effect=fake_get) as mocked_get:
            counters = self.env['mailing.trace']._brevo_catchup(7)
        self.assertEqual(mocked_get.call_count, 6)
        # le hard bounce est traité ; le spam arrive sur une adresse déjà en liste noire
        self.assertEqual(counters, {'processed': 1, 'ignored': 1, 'not_found': 0})
        self.assertEqual(self.trace.trace_status, 'bounce')
        self.assertTrue(self._is_blacklisted())

    def test_cron_without_api_key(self):
        """Sans clé API, le cron ne fait rien et ne plante pas (cron en échec chaque nuit sinon)."""
        self.env['ir.config_parameter'].sudo().set_param('brevo_api_key', False)
        with mock.patch('odoo.addons.brevo_connector.models.brevo.requests.get') as mocked_get:
            self.env['mailing.trace']._cron_brevo_catchup()
        mocked_get.assert_not_called()

    def test_cron_reads_last_days(self):
        """Le cron relit les 3 derniers jours, aujourd'hui inclus."""
        self.env['ir.config_parameter'].sudo().set_param('brevo_api_key', "cle-de-test")
        with mock.patch('odoo.addons.brevo_connector.models.brevo.requests.get', return_value=self._mock_response([])) as mocked_get:
            self.env['mailing.trace']._cron_brevo_catchup()
        today = fields.Date.context_today(self.env['mailing.trace'])
        params = mocked_get.call_args.kwargs['params']
        self.assertEqual(params['endDate'], today.isoformat())
        self.assertEqual(params['startDate'], fields.Date.subtract(today, days=2).isoformat())

    def test_cron_is_installed(self):
        cron = self.env.ref('brevo_connector.brevo_catchup_scheduler')
        self.assertEqual((cron.interval_number, cron.interval_type), (1, 'days'))

    def test_catchup_api_error(self):
        self.env['ir.config_parameter'].sudo().set_param('brevo_api_key', "cle-de-test")
        response = mock.Mock(status_code=401, text="Key not found")
        with mock.patch('odoo.addons.brevo_connector.models.brevo.requests.get', return_value=response):
            with self.assertRaises(ValidationError):
                self.env['mailing.trace']._brevo_catchup(7)


@tagged("post_install", "-at_install")
class TestBrevoWebhook(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('brevo_webhook_token', "jeton-secret")
        self.partner = self.env['res.partner'].create({'name': "Contact webhook Brevo", 'email': "webhook.brevo@example.com"})

    def _post(self, token, payload):
        return self.url_open(
            '/brevo/webhook/%s' % token, data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}, allow_redirects=False)

    def test_wrong_token_is_refused(self):
        response = self._post("mauvais-jeton", {'event': 'hard_bounce', 'email': "webhook.brevo@example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.env['mail.blacklist'].search([('email', '=', "webhook.brevo@example.com")]))

    def test_webhook_disabled_without_token(self):
        self.env['ir.config_parameter'].sudo().set_param('brevo_webhook_token', False)
        response = self._post("jeton-secret", {'event': 'hard_bounce', 'email': "webhook.brevo@example.com"})
        self.assertEqual(response.status_code, 403)

    def test_hard_bounce_via_webhook(self):
        response = self._post("jeton-secret", {'event': 'hard_bounce', 'email': "webhook.brevo@example.com", 'reason': "550"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.env['mail.blacklist'].search([('email', '=', "webhook.brevo@example.com")]))

    def test_invalid_json(self):
        response = self.url_open('/brevo/webhook/jeton-secret', data="pas du json", headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 400)
