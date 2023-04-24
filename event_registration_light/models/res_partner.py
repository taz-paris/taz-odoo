from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class resPartner(models.Model):
    _inherit = "res.partner"

    #contact_created_on_public_event_registration = fields.Boolean("Contact créé suite à l'inscription à un évènement", help="When a guest fill the public event registration form, if its email can't be found in any partner, a new partner is created with that boolean set True")
    event_registration_ids = fields.One2many('event.registration', 'partner_id',  groups="event.group_event_user, event.group_event_registration_desk, event.group_event_manager")
