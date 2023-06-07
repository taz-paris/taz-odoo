from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class projectAccountingAccountMove(models.Model):
    _inherit = "account.move"


    @api.depends('bank_partner_id')
    def _compute_partner_bank_id(self):
        super()._compute_partner_bank_id()
        for move in self:
            if move.partner_id.default_invoice_payement_bank_account:
                move.partner_bank_id = move.partner_id.default_invoice_payement_bank_account
            #else :
            #    bank_ids = move.bank_partner_id.bank_ids.filtered(
            #        lambda bank: not bank.company_id or bank.company_id == move.company_id)
            #    move.partner_bank_id = bank_ids[0] if bank_ids else False
    # TODO : rendre le move.partner_bank_id obligatoire pour les factures clients (out_invoice)
        # si le partenr n'a pas de compte par defaut, l'ADV devra en mettre un manuellement sur la facture
    # TODO : quand move.partner_bank_id change ; sur le compte bancaire par défaut sur le partenaire n'est pas renseigner, proposer à l'utilisateur de l'ajouter sur la fiche du partner (wizzard de validation) 
    
    def _compute_payments_widget_to_reconcile_info(self):
        _logger.info('_compute_payments_widget_to_reconcile_info')

        super()._compute_payments_widget_to_reconcile_info()

        for move in self:
            payments_widget_vals = move.invoice_outstanding_credits_debits_widget
            if not payments_widget_vals:
                continue
            new_content = []

            #lines = move._compute_payments_widget_to_reconcile_info()
            _logger.info(payments_widget_vals['content'])
            for line in payments_widget_vals['content']:
                payment = self.env['account.payment'].search([('id', '=', line['account_payment_id'])])[0]
                #On supprime les paiements d'avance, s'ils ne concernent pas le sale.order d'au moins une des lignes de la factures
                if payment.advance_sale_order_id and payment.advance_sale_order_id.id not in move.line_ids.sale_line_ids.order_id.ids :
                    continue
                new_content.append(line)

            payments_widget_vals['content'] = new_content
            _logger.info(payments_widget_vals)
            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = len(new_content)
