# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class tazContact(models.Model):
     _name = "taz.contact"


     first_name = fields.Char(string="Prénom")
     name = fields.Char(index=True, default_export_compatible=True)
     parent_id = fields.Many2one('res.partner', string='Related Company', index=True)
     user_id = fields.Many2one(
        'res.users', string='Salesperson',
        compute='_compute_user_id',
        precompute=True,  # avoid queries post-create
        readonly=False, store=True,
        help='The internal user in charge of this contact.')
     comment = fields.Html(string='Notes')
     active = fields.Boolean(default=True)
     function = fields.Char(string='Job Position')
     email = fields.Char()
     phone = fields.Char(unaccent=False)
     mobile = fields.Char(unaccent=False)
     category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                    column2='category_id', string='Tags', default=_default_category)

     parent_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='parent_id.industry_id', store=True)
     business_action_ids = fields.One2many('taz.business_action', 'partner_id') 


     def name_get(self):
         res = []
         for rec in self:
                 res.append((rec.id, "%s %s (%s)" % (rec.first_name, rec.name or "", rec.parent_id.name or "")))
         return res

     @api.constrains('email')
     def _check_email(self):
         count_email = self.search_count([('email', '=', self.email), ('is_company', '=', False)])
         if count_email > 1 and self.email is not False:
             raise ValidationError(_('Cette adresse email est déjà utilisée sur une autre fiche contact. Enregistrement impossible (il ne faudrait pas créer des doublons de contact ;-)) !'))
