from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

    
class resPartnerMassCategory(models.TransientModel):
     _name = 'taz.res_partner_mass_category'
     _description = "resPartnerMassCategory"

     name = fields.Char("Name")
     add_category_ids = fields.Many2many('res.partner.category', column1='res_partner_mass_category_id',
                                    column2='category_id', relation='wizard_add_category_ids', string='Tags à ajouter') 

     remove_category_ids = fields.Many2many('res.partner.category', column1='res_partner_mass_category_id',
                                    column2='category_id', relation='wizard_remove_category_ids', string='Tags à supprimer') 

     partner_ids = fields.Many2many('res.partner', column1='res_partner_mass_category_id',
             column2='partner_id', relation='wizard_category_partners_ids', string='Contacts') 

     def action_validate(self):
         _logger.info('------------ resPartnerMassCategory VALIDATE')
         _logger.info(self.add_category_ids)
         _logger.info(self.remove_category_ids)
         _logger.info(self.partner_ids)
         for c in self.remove_category_ids:
             if c in self.add_category_ids:
                raise ValidationError(_('Opération impossible. Le tag %s est présent dans la liste des tags à ajouter et celle des tags à supprimer. Ce n\'est pas cohérent.' % c.name))
         for partner in self.partner_ids:
            for tag2add in self.add_category_ids:
                if tag2add not in partner.category_id:
                    _logger.info('>>> Ajout tag %s sur le partner %s' % (tag2add, partner.name))
                    partner.category_id = [(4,tag2add.id)]
            for tag2remove in self.remove_category_ids:
                if tag2remove in partner.category_id:
                    _logger.info('>>> Suppression tag %s sur le partner %s' % (tag2remove, partner.name))
                    partner.category_id = [(3,tag2remove.id)]
                    

