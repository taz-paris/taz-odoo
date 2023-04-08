from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)


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

    @api.depends('user_id', 'partner_id', 'partner_id.business_action_ids', 'partner_id.business_action_ids.date_deadline', 'partner_id.business_action_ids.state')
    def _compute_date_last_business_action(self_list):
         for self in self_list :
             res = None
             for action in self.partner_id.business_action_ids:
                 if action.state == 'done' and self.user_id in action.user_ids :
                     if res == None or action.date_deadline > res:
                         res = action.date_deadline
             self.date_last_business_action = res

    user_id = fields.Many2one('res.users', string='Tasmanien', required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Contact', required=False)
        #, default=lambda self: self.env['taz.contact_user_link'].search([('id', '=', self._context.get("default_partner_id"))], limit=1))
        #self._context.get("default_partner_id"))
    date_last_business_action = fields.Date('Date du dernier RDV', compute=_compute_date_last_business_action, store=True)
    #desired_meeting_frequency = fields.Selection([
    #        ('year', '1 fois par an'),
    #        ('year2', '2 fois par an'),
    #        ('year3', '3 fois par an'),
    #        ('year4', '4 fois par an'),
    #    ], srting="Fréquence de contact"),
    #RDV to plan before
    proximity_level = fields.Selection([
            ('0', "je le connais de vue"),
            ('1', "j'ai déjà travaillé avec lui"),
            ('2', "j'ai eu une collaboration intense avec lui"),
            ('3', "j'ai son numéro de portable et je peux l'appeler à 22h"),
        ], string="Niveau de proximité") 
