from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

    
class resPartnerMassContactUserLink(models.TransientModel):
    _name = 'taz.res_partner_contact_user_link'
    _description = "resPartnerMassContactUserLink"

    name = fields.Char("Name")

    partner_ids = fields.Many2many('res.partner', column1='res_partner_contact_user_link_id',
                                   column2='partner_id', relation='wizard_contact_user_link_partners_ids', string='Contacts')

    def action_validate(self):
        #_logger.info('------------ resPartnerMassCategory VALIDATE')
        #_logger.info(self.add_category_ids)
        #_logger.info(self.remove_category_ids)
        #_logger.info(self.partner_ids)
        for partner in self.partner_ids:
            if partner.is_company:
                raise ValidationError(_('Une entreprise est sélectionnée. Opération impossible.'))
            else:
                target_contact_user_link_ids = self.env['taz.contact_user_link'].search([
                    ('partner_id', '=', partner.id),
                    ('user_id', '=', self.env.user.id)
                ])
                if len(target_contact_user_link_ids) == 0:
                    target_contact_user_link_id = self.env['taz.contact_user_link'].create({
                        'partner_id': partner.id,
                        'user_id': self.env.user.id
                    })


