from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime

PROTECTED_FIELD_LIST = [
            'name',
            'long_company_name', 
            'parent_id',
            'is_company',
            'type',
            'street',
            'street2',
            'street3',
            'city',
            'state_id',
            'zip',
            'country_id',
            'child_ids_address',
            'ref',
            'vat',
            'company_registry',
            'siren',
            'nic',
            'siret',
            'external_auxiliary_code',
            'currency_id',
            'property_account_receivable_id',
            'property_account_payable_id',
            'property_payment_term_id',
            'property_supplier_payment_term_id',
            'property_account_position_id',
            'default_invoice_payement_bank_account',
        ]

class projectAccountingResPartner(models.Model):
     _inherit = "res.partner"

     def write(self, vals):
         for rec in self :
             #_logger.info(rec.name)
             #_logger.info(vals)
             if rec._precompute_protected() and not (self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')):
                 if any(field in PROTECTED_FIELD_LIST for field in vals.keys()):
                    raise ValidationError(_("Cette fiche est protégée : seul un ADV peut modifier le nom, le libellé long, le groupe, l'adresse postale, et les données comptables (onglet Facturation) de cette fiche."))
         super().write(vals)

     def _precompute_protected(self):
        protected = False
        if self.is_company :
            if self.invoice_ids or self.sale_order_ids or self.purchase_order_count :
                protected = True
        return protected
        
     @api.depends('invoice_ids', 'sale_order_ids', 'purchase_order_count')
     def _compute_protected_partner(self):
         for rec in self:
             protected = rec._precompute_protected()
             rec.is_protected_partner = protected
        #TODO vérifier que invoices ids prend bien aussi les accoun.move liés par l'adresse de facturation/livraison


     @api.depends('project_ids', 'project_ids.date_start', 'project_ids.partner_id', 'project_ids.stage_is_part_of_booking')
     def compute_has_project_started_this_year(self):
         for rec in self:
             count = self.env['project.project'].search_count([
                            ('partner_id', '=', rec.id),
                            ('stage_is_part_of_booking', '=', True),
                            ('date_start', '>=', datetime.today().replace(month=1, day=1)),
                            ('date_start', '<=', datetime.today().replace(month=12, day=31))
                        ])
             res = False
             if count > 0 :
                 res = True
             rec.has_project_started_this_year = res

     def get_book_by_year(self, year):
         #_logger.info('-- RES.PARTNER get_book_by_year')
         res = 0.0
         for project in self.project_ids:
             res += project.get_book_by_year(year)
         #_logger.info(res)
         return res

     @api.constrains('external_auxiliary_code')
     def check_external_auxiliary_code_consistency(self):
         for rec in self:
             if rec.external_auxiliary_code and len(rec.external_auxiliary_code) > 8:
                 raise ValidationError(_("Le code auxiliaire CEGB - Quadratus ne peut pas faire plus de 8 caractères."))
            
     project_ids = fields.One2many('project.project', 'partner_id', string="Projets")
     has_project_started_this_year = fields.Boolean('Un projet a débuté cette année', compute=compute_has_project_started_this_year, store=True)
     is_protected_partner = fields.Boolean('Fiche entreprise protégée', compute=_compute_protected_partner, help="Une fiche est protégée lorsqu'un objet comptable ou paracomptable (bon de commande client/fournisseur) le référence. Dans ce cas, la fiche ne peut être modifiée que par un ADV.")


