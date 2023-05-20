from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime


class projectAccountingResPartner(models.Model):
     _inherit = "res.partner"

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
         project_ids = self.env['project.project'].search([
                            ('partner_id', '=', self.id),
                            ('stage_is_part_of_booking', '=', True),
                            ('date_start', '>=', datetime(year, 1, 1)),
                            ('date_start', '<=', datetime(year, 12, 31))
                        ])
         res = 0.0
         for project in project_ids:
             res += project.order_amount
         return res

     project_ids = fields.One2many('project.project', 'partner_id', string="Projets")
     has_project_started_this_year = fields.Boolean('Un projet a débuté cette année', compute=compute_has_project_started_this_year, store=True)

     def _get_default_invoice_payement_bank_account_domain(self):
         return [('partner_id', '=', self.env.company.id)]

     default_invoice_payement_bank_account = fields.Many2one('res.partner.bank', 
             string="Compte bancaire de paiement", 
             help="Compte bancaire qui apparaitra par défaut sur les factures envoyées à ce client, et sur lequel le client devra payer la facture.", 
             domain=_get_default_invoice_payement_bank_account_domain)
