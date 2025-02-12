from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

    
class resPartnerMassEventRegistrationLine(models.TransientModel):
    _name = "res_partner_mass_event_registration_line"
    _description = "Wizard for mass event registration line"

    wizard_id = fields.Many2one('res_partner_mass_event_registration')
    partner_id = fields.Many2one('res.partner', string='Contacts', required=True)

    add_contact_user_link = fields.Boolean("Ajouter à mon plan d'intimité", default=True)
    add_event_registration_owner = fields.Boolean("Responsable de l'invitation", default=True)

class resPartnerMassEventRegistration(models.TransientModel):
     _name = 'res_partner_mass_event_registration'
     _description = "Wizard for mass event registration"

     def _default_line_ids(rec):
         res = []
         if 'default_contact_user_link_ids' in rec.env.context.keys():
             link_ids = rec.env.context.get('default_contact_user_link_ids')
             for link in rec.env['taz.contact_user_link'].search([('id', 'in', link_ids)]):
                 line_id = rec.env['res_partner_mass_event_registration_line'].create({
                     'wizard_id': rec.id,
                     'partner_id': link.partner_id.id
                 })
                 res.append(line_id.id)

         if 'default_partner_ids' in rec.env.context.keys():
            partner_ids = rec.env.context.get('default_partner_ids')
            for partner_id in partner_ids:
                line_id = rec.env['res_partner_mass_event_registration_line'].create({
                    'wizard_id': rec.id,
                    'partner_id': partner_id
                })
                res.append(line_id.id)

         return res

     add_event_id = fields.Many2one('event.event', string='Évènement', required=True)
     line_ids = fields.One2many('res_partner_mass_event_registration_line', 'wizard_id', string="Contacts à inviter", default=_default_line_ids)

     def action_validate(self):
         _logger.info('------------ resPartnerMassEventRegistration VALIDATE')
         _logger.info(self.add_event_id)
         _logger.info(self.partner_ids)

         for line in self.lines_ids:
            partner = line.partner_id
            if partner.is_company:
                raise ValidationError(_('Une entreprise est sélectionnée. Opération impossible.'))
            if self.add_event_id:
                already_registered = self.env['event.registration'].search_count([('partner_id', '=', partner.id), ('event_id', '=', self.add_event_id.id)])
                if not already_registered :
                    _logger.info('>>> Ajout event.registration %s sur le partner %s' % (self.add_event_id.name, partner.name))
                    #create registration
                    registration_dict = {'event_id': self.add_event_id.id, 'partner_id': partner.id, 'email': partner.email,
                     'name': partner.first_name + " " + partner.name}
                    registration_id = self.env['event.registration'].create(registration_dict)
                #add contact user link
                if line.add_contact_user_link:
                    target_contact_user_link_ids = self.env['taz_common.contact_user_link'].search([
                        ('partner_id', '=', partner.id),
                        ('user_id', '=', self.env.user.id)
                    ])
                    if len(target_contact_user_link_ids) == 0:
                        target_contact_user_link_id = self.env['taz_common.contact_user_link'].create({
                            'partner_id': partner.id,
                             'user_id': self.env.user.id
                             })
                #add event registration owner
                if line.add_event_registration_owner:
                    target_registration_ids = self.env['event.registration'].search([
                        ('event_id', '=', self.add_event_id.id),
                        ('partner_id', '=', partner.id),
                        ('contact_user_link_id', '=', False)
                    ])
                    if len(target_registration_ids) == 1:
                        target_contact_user_link_ids = self.env['taz_common.contact_user_link'].search([
                            ('partner_id', '=', partner.id),
                            ('user_id', '=', self.env.user.id)
                        ])
                        if len(target_contact_user_link_ids) == 1:
                            target_registration_ids[0].contact_user_link_id = target_contact_user_link_ids[0]