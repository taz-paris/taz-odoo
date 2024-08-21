from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

    
class resPartnerMassEventRegistration(models.TransientModel):
     _name = 'res_partner_mass_event_registration'
     _description = "Wizard for mass event registration"

     def _default_partner_ids(rec):
         if 'default_contact_user_link_ids' in rec.env.context.keys():
             link_ids = rec.env.context.get('default_contact_user_link_ids')
             p_ids = []
             for link in rec.env['taz.contact_user_link'].search([('id', 'in', link_ids)]):
                 p_ids.append(link.partner_id.id)
             return p_ids


     add_event_id = fields.Many2one('event.event', string='Évènement', required=True) 
     partner_ids = fields.Many2many('res.partner', column1='registration_id',
             column2='partner_id', relation='wizard_event_registration_partner_ids', string='Contacts', required=True, default=_default_partner_ids) 


     def action_validate(self):
         _logger.info('------------ resPartnerMassEventRegistration VALIDATE')
         _logger.info(self.add_event_id)
         _logger.info(self.partner_ids)

         for partner in self.partner_ids:
            if partner.is_company:
                raise ValidationError(_('Une entreprise est sélectionnée. Opération impossible.'))
            if self.add_event_id:
                already_registered = self.env['event.registration'].search_count([('partner_id', '=', partner.id), ('event_id', '=', self.add_event_id.id)])
                if not already_registered :
                    _logger.info('>>> Ajout event.registration %s sur le partner %s' % (self.add_event_id.name, partner.name))
                    #create registration
                    target = self.env['event.registration'].create({'event_id' : self.add_event_id.id, 'partner_id' : partner.id, 'email' : partner.email, 'name' : partner.first_name + " " + partner.name})
