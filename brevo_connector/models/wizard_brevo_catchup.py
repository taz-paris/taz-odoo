from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .mailing_trace import BREVO_CATCHUP_MAX_DAYS

import logging
_logger = logging.getLogger(__name__)


class wizardBrevoCatchup(models.TransientModel):
    _name = 'wizard_brevo_catchup'
    _description = "Assistant de rattrapage des événements Brevo"

    days = fields.Integer(
        "Nombre de jours", default=7, required=True,
        help="Période relue chez Brevo, aujourd'hui inclus (90 jours maximum). "
             "Choisir une période qui couvre l'arrêt de TazForce. Les événements déjà traités sont ignorés.")

    @api.constrains('days')
    def _check_days(self):
        for rec in self:
            if rec.days < 1 or rec.days > BREVO_CATCHUP_MAX_DAYS:
                raise ValidationError(_("Le rattrapage Brevo porte sur 1 à %s jours.", BREVO_CATCHUP_MAX_DAYS))

    def action_catchup(self):
        self.ensure_one()
        counters = self.env['mailing.trace']._brevo_catchup(self.days)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rattrapage Brevo terminé"),
                'message': _(
                    "%(processed)s événement(s) traité(s), %(ignored)s déjà traité(s) ou ignoré(s), "
                    "%(not_found)s bounce(s) sans envoi TazForce correspondant.",
                    **counters),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
