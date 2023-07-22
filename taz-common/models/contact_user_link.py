from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
import datetime
from dateutil.relativedelta import relativedelta
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class ContactUserLinkFrequency(models.Model):
    _name = "taz.contact_user_link_frequency"
    _description = "Frequency of the relation of an user and a customer/contact"

    name = fields.Char("Libellé")
    day_number = fields.Integer("Nombre de jours")

class ContactUserLink(models.Model):
    _name = "taz.contact_user_link"
    _description = "Record attributes of the relation of an user and a customer/contact"
    _sql_constraints = [
        ('contact_user_uniq', 'UNIQUE (partner_id, user_id)',  "Impossible d'enregistrer deux liens pour un même contact et un même utilisatuer.")
    ] 
    
    """
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        _logger.info("########################@")
        _logger.info(res)
        res['partner_id'] = self._context.get("default_partner_id")
        res['partner_id'] = self._context.get("default_partner_id")
        _logger.info(res)
        return res
        """

    @api.model
    def create(self, vals):
        if not vals.get("partner_id"):
            vals["partner_id"] = self._context.get("default_partner_id")
        return super().create(vals)

    @api.depends('user_id', 'partner_id', 'partner_id.business_action_ids', 'partner_id.business_action_ids.date_deadline', 'partner_id.business_action_ids.state', 'target_contact_frequency_id', 'target_contact_frequency_id.day_number')
    def _compute_date_business_action(self):
        _logger.info("-- _compute_date_business_action")
        for rec in self :
            partner_id = rec.partner_id
            #if rec._origin.id :
            #    partner_id = rec._origin
            #else:
            #    partner_id = rec.partner_id
            #_logger.info(partner_id)
            passed_business_action = rec.env['taz.business_action'].search(
               [
                   ('date_deadline', '<=', datetime.date.today()), 
                   ('state', '=', 'done'),
                   ('user_ids', 'in', rec.user_id.id),
                   ('partner_id', '=', partner_id.id),
               ], order="date_deadline desc")
            #_logger.info(passed_business_action)
            rec.is_late = False
            if len(passed_business_action):
                rec.last_business_action_id = passed_business_action[0]
                rec.date_last_business_action = passed_business_action[0].date_deadline
                if rec.target_contact_frequency_id :
                    rec.next_meeting_before = passed_business_action[0].date_deadline + relativedelta(days=rec.target_contact_frequency_id.day_number)
                    if rec.next_meeting_before < datetime.date.today():
                        rec.is_late = True
            else :
                rec.last_business_action_id = False
                rec.date_last_business_action = False
            future_business_action = rec.env['taz.business_action'].search(
               [
                   ('date_deadline', '>', datetime.date.today()), 
                   #('state', '=', 'done'),
                   ('user_ids', 'in', rec.user_id.id),
                   ('partner_id', '=', partner_id.id),
               ], order="date_deadline asc")
            if len(future_business_action):
                rec.next_business_action_id = future_business_action[0]
            else :
                rec.next_business_action_id = False

    user_id = fields.Many2one('res.users', string='Tasmanien', required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Contact', required=False)
        #, default=lambda self: self.env['taz.contact_user_link'].search([('id', '=', self._context.get("default_partner_id"))], limit=1))
        #self._context.get("default_partner_id"))
    last_business_action_id = fields.Many2one('taz.business_action', string='Dernière action au statut FAIT', help="Dernière action commerciale au statut FAIT de ce tasmanien avec ce contact.", compute=_compute_date_business_action)
    date_last_business_action = fields.Date('Date dernière action au statut FAIT', compute=_compute_date_business_action, store=True)
    next_business_action_id = fields.Many2one('taz.business_action', string='Prochaine action', help="Prochaine action commerciale (quel que soit le statut) de ce tasmanien avec ce contact.", compute=_compute_date_business_action)
    is_late = fields.Boolean('En retard', help="La dernière action commerciale faite par ce tasmanien auprès de ce contact est plus ancienne que la fréquence souhaitée.", compute=_compute_date_business_action, store=True, default=False)
    next_meeting_before = fields.Date('À revoir avant le', compute=_compute_date_business_action, store=True)
    
    #RDV to plan before
    proximity_level = fields.Selection([
            ('0', "0 - je le connais de vue"),
            ('1', "1 - j'ai déjà travaillé avec lui"),
            ('2', "2 - j'ai eu une collaboration intense avec lui"),
            ('3', "3 - j'ai son numéro de portable et je peux l'appeler à 22h"),
        ], string="Niveau de proximité") 
    target_contact_frequency_id = fields.Many2one('taz.contact_user_link_frequency', string="Fréquence de contact")
    comment = fields.Html("Commentaire")
    communication_preference = fields.Selection([
            ('email-tu', "email auto - TU"),
            ('email-vous', "email auto - VOUS"),
            ('email-perso', "email personalisé"),
            ('paper-perso', "papier personalisé"),
        ], string="Pref. com. voeux") 
