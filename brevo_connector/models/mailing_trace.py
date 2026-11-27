import datetime

from markupsafe import Markup

from odoo import api, fields, models, tools, _

from odoo.addons.base.models.ir_cron import _intervalTypes

from .brevo import ClientRestBrevo

import logging
_logger = logging.getLogger(__name__)

##################################################################
##########                SET PARAMETERS                ##########
##################################################################

FALLBACK_TRACE_DAYS = 30  # sans Message-ID, on rattache l'événement au dernier envoi des 30 jours précédents

# Nom de l'événement dans le webhook Brevo => type interne
BREVO_WEBHOOK_EVENTS = {
    'hard_bounce': 'hard_bounce',
    'soft_bounce': 'soft_bounce',
    'invalid_email': 'invalid_email',
    'blocked': 'blocked',
    'spam': 'spam',
    'unsubscribed': 'unsubscribed',
}
# Nom de l'événement dans l'API Brevo (/smtp/statistics/events) => type interne
BREVO_API_EVENTS = {
    'hardBounces': 'hard_bounce',
    'softBounces': 'soft_bounce',
    'invalid': 'invalid_email',
    'blocked': 'blocked',
    'spam': 'spam',
    'unsubscribed': 'unsubscribed',
}
# Événements qui signifient que l'email n'a pas été distribué : trace en « Rebondi » + compteur de bounces (logique standard Odoo)
BOUNCE_EVENTS = ('hard_bounce', 'soft_bounce', 'invalid_email', 'blocked')
# Événements qui mettent l'adresse en liste noire immédiatement (Brevo n'envoie de toute façon plus rien à ces adresses)
BLACKLIST_EVENTS = ('hard_bounce', 'invalid_email', 'blocked', 'spam', 'unsubscribed')


class brevoMailingTrace(models.Model):
    _inherit = 'mailing.trace'

    # ===================================================================
    # POINTS D'ENTRÉE
    # ===================================================================
    @api.model
    def _brevo_process_webhook_payload(self, payload):
        """Traite le contenu d'un appel du webhook transactionnel Brevo (un événement, ou une liste si l'envoi groupé est activé)."""
        events = payload if isinstance(payload, list) else [payload]
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = BREVO_WEBHOOK_EVENTS.get(event.get('event'))
            if not event_type:
                _logger.debug("Webhook Brevo : événement %s ignoré", event.get('event'))
                continue
            self._brevo_process_event(
                event_type,
                event.get('email'),
                message_id=event.get('message-id'),
                reason=event.get('reason'),
                event_date=self._brevo_parse_date(event.get('ts_event') or event.get('date')),
            )

    @api.model
    def _cron_brevo_catchup(self):
        """Cron journalier : relit via l'API Brevo les événements depuis le jour du dernier passage réussi du cron (inclus)
        jusqu'à aujourd'hui, pour rattraper ceux que le webhook n'a pas reçus (TazForce arrêté, erreur de traitement...).
        Au premier passage, seule la journée en cours est relue (pas de reprise d'historique).
        """
        if not self.env['ir.config_parameter'].sudo().get_param("brevo_api_key"):
            _logger.info("Rattrapage Brevo automatique non lancé : le paramètre système brevo_api_key n'est pas valorisé")
            return
        cron = self.env['ir.cron'].sudo().browse(self.env.context.get('cron_id')) or self.env.ref('brevo_connector.brevo_catchup_scheduler')
        end_date = fields.Date.context_today(self)
        start_date = self._brevo_cron_last_success_date(cron) or end_date
        # date du cron dans le futur (base restaurée, horloge corrigée...) : on relit au moins la journée en cours
        self._brevo_catchup(min(start_date, end_date), end_date)

    @api.model
    def _brevo_cron_last_success_date(self, cron):
        """Jour du dernier passage réussi du cron, False s'il n'a jamais tourné.

        Odoo met à jour la date de dernière exécution (lastcall) même quand un passage échoue. Après un ou plusieurs
        échecs (failure_count > 0), le dernier passage réussi est donc celui qui précède le premier échec
        (first_failure_date) d'un intervalle du cron. Ces deux champs sont remis à zéro par Odoo au premier succès.
        """
        if cron.failure_count and cron.first_failure_date:
            last_success = cron.first_failure_date - _intervalTypes[cron.interval_type](cron.interval_number)
        else:
            last_success = cron.lastcall
        return last_success and fields.Datetime.context_timestamp(self, last_success).date()

    @api.model
    def _brevo_catchup(self, start_date, end_date):
        """Relit via l'API Brevo les événements du `start_date` au `end_date` inclus et les traite.

        Les événements déjà traités (par le webhook ou un précédent passage) sont ignorés.
        Renvoie le nombre d'événements par résultat : {'processed': x, 'ignored': y, 'not_found': z}.
        """
        client = ClientRestBrevo(self.env)
        counters = {'processed': 0, 'ignored': 0, 'not_found': 0}
        for api_event, event_type in BREVO_API_EVENTS.items():
            for event in client.get_transactional_events(api_event, start_date, end_date):
                result = self._brevo_process_event(
                    event_type,
                    event.get('email'),
                    message_id=event.get('messageId'),
                    reason=event.get('reason'),
                    event_date=self._brevo_parse_date(event.get('date')),
                )
                counters[result] += 1
        _logger.info("Rattrapage Brevo du %s au %s : %s", start_date, end_date, counters)
        return counters

    # ===================================================================
    # TRAITEMENT D'UN ÉVÉNEMENT
    # ===================================================================
    @api.model
    def _brevo_process_event(self, event_type, email, message_id=False, reason=False, event_date=False):
        """Applique un événement Brevo dans TazForce.

        - bounce (hard, soft, invalide, bloqué) : on retrouve l'envoi (mailing.trace) et on applique la logique standard
          d'Odoo, comme pour un bounce reçu par email : trace en « Rebondi », compteur de bounces de tous les
          enregistrements portant cette adresse, liste noire automatique après 5 bounces espacés d'au moins une semaine.
          Un envoi déjà en « Rebondi » n'est pas retraité (appel webhook rejoué, rattrapage après le webhook...).
        - hard bounce, invalide, bloqué, spam, désinscription : liste noire immédiate, avec le motif.

        Renvoie 'processed' si quelque chose a été modifié, 'ignored' si l'événement était déjà traité ou inexploitable,
        'not_found' si aucun envoi TazForce ne correspond à ce bounce.
        """
        email_normalized = tools.email_normalize(email or '')
        if not email_normalized or event_type not in BREVO_WEBHOOK_EVENTS.values():
            _logger.debug("Événement Brevo ignoré : type=%s email=%s", event_type, email)
            return 'ignored'

        result = 'ignored'
        if event_type in BOUNCE_EVENTS:
            trace = self._brevo_find_trace(email_normalized, message_id, event_date)
            if not trace:
                result = 'not_found'
            elif trace.trace_status != 'bounce':
                trace._brevo_set_bounced(email_normalized, reason)
                result = 'processed'

        if event_type in BLACKLIST_EVENTS:
            if self._brevo_blacklist(email_normalized, event_type, reason):
                result = 'processed'

        _logger.info("Événement Brevo %s pour %s : %s (Message-ID %s, motif : %s)", event_type, email_normalized, result, message_id, reason)
        return result

    @api.model
    def _brevo_find_trace(self, email_normalized, message_id=False, event_date=False):
        """Retrouve l'envoi concerné : d'abord par Message-ID, sinon le dernier envoi à cette adresse dans les 30 jours
        précédant l'événement."""
        if message_id:
            message_id = message_id.strip().strip('<>')
            trace = self.search([('message_id', 'in', [message_id, '<%s>' % message_id])], order='id desc', limit=1)
            if trace:
                return trace
        reference_date = event_date or fields.Datetime.now()
        return self.search([
            ('trace_type', '=', 'mail'),
            ('email', '=', email_normalized),
            ('trace_status', 'in', ('sent', 'open', 'reply', 'bounce')),
            ('sent_datetime', '>=', reference_date - datetime.timedelta(days=FALLBACK_TRACE_DAYS)),
            ('sent_datetime', '<=', reference_date + datetime.timedelta(days=1)),  # marge : fuseau horaire de la date Brevo
        ], order='sent_datetime desc, id desc', limit=1)

    def _brevo_set_bounced(self, email_normalized, reason):
        """Applique un bounce sur cet envoi en réutilisant le traitement standard d'Odoo des bounces reçus par email
        (mail.thread._routing_handle_bounce, complété par mass_mailing)."""
        self.ensure_one()
        bounced_message = self.env['mail.message']
        if self.message_id:
            bounced_message = bounced_message.search([('message_id', '=', self.message_id)], limit=1)
        message_dict = {
            'bounced_email': email_normalized,
            'bounced_partner': self.env['res.partner'].search([('email_normalized', '=', email_normalized)]),
            'bounced_msg_ids': [self.message_id] if self.message_id else [],
            'bounced_message': bounced_message,
            'body': reason or _("Bounce signalé par Brevo"),
            # utilisés uniquement dans les logs du traitement standard
            'email_from': 'Brevo',
            'to': email_normalized,
            'message_id': self.message_id or '',
        }
        self.env['mail.thread']._routing_handle_bounce(False, message_dict)
        if self.trace_status != 'bounce':
            # sans Message-ID, le traitement standard ne retrouve pas l'envoi
            self.set_bounced(bounce_message=reason or _("Bounce signalé par Brevo"))

    @api.model
    def _brevo_blacklist(self, email_normalized, event_type, reason=False):
        """Met l'adresse en liste noire avec le motif Brevo. Renvoie False si elle y était déjà."""
        blacklist = self.env['mail.blacklist']
        if blacklist.search([('email', '=', email_normalized)], limit=1):
            return False
        messages = {
            'hard_bounce': _("Adresse ajoutée automatiquement à la liste noire : hard bounce signalé par Brevo."),
            'invalid_email': _("Adresse ajoutée automatiquement à la liste noire : adresse invalide signalée par Brevo."),
            'blocked': _("Adresse ajoutée automatiquement à la liste noire : adresse bloquée par Brevo."),
            'spam': _("Adresse ajoutée automatiquement à la liste noire : le destinataire a signalé un email comme spam (via Brevo)."),
            'unsubscribed': _("Adresse ajoutée automatiquement à la liste noire : le destinataire s'est désinscrit via Brevo."),
        }
        message = Markup('<p>%s</p>') % messages[event_type]
        if reason:
            message += Markup('<p>%s</p>') % _("Motif Brevo : %s", reason)
        blacklist._add(email_normalized, message=message)
        return True

    # ===================================================================
    # OUTILS
    # ===================================================================
    @api.model
    def _brevo_parse_date(self, value):
        """Convertit une date Brevo (timestamp Unix, ou texte ISO avec ou sans fuseau) en datetime UTC naïf."""
        if not value:
            return False
        try:
            if isinstance(value, (int, float)):
                return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc).replace(tzinfo=None)
            date = datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (ValueError, OverflowError, OSError):
            _logger.warning("Date Brevo illisible : %s", value)
            return False
        if date.tzinfo:
            date = date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return date
