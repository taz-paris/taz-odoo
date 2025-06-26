from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class event(models.Model):
    _inherit = "event.event"


    def _get_registration_form_url(self):
        for rec in self :
            if rec.id :
                #url = rec._notify_get_action_link('controller', controller='/eventlight/'+str(rec.id)+'/registration/new')
                web_base_url = self.env['ir.config_parameter'].sudo().get_param("web.base.url")
                url = web_base_url + '/eventlight/' + str(rec.id) + '/registration/new'
                rec.registration_form_url = url
            else:
                rec.registration_form_url = False

    @api.depends('seats_max', 'registration_ids.state', 'registration_ids.active')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0
        super()._compute_seats()
        for event in self:
            event.seats_taken = event.seats_reserved + event.seats_used


    registration_form_url = fields.Char("URL du formulaire d'inscription", compute=_get_registration_form_url)
    description_web_form = fields.Html("Bloc HTML affiché sur le formulaire d'inscription")
    invitation_mail_template = fields.Many2one("ir.ui.view", "Template du mail d'invitation", domain=[('type', '=', 'qweb')])
    invitation_cc_address = fields.Char('Adresse en CC')
    event_registrations_open = fields.Boolean(store=True)
    company_id = fields.Many2one(default=False)


class EventType(models.Model):
    _inherit = 'event.type'

    def _default_event_mail_type_ids(self):
        return []
        """
        return [(0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 0,
                  'interval_unit': 'now',
                  'interval_type': 'after_sub',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_subscription').id,
                 }),
                (0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 1,
                  'interval_unit': 'hours',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 }),
                (0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 3,
                  'interval_unit': 'days',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 })]
        """
