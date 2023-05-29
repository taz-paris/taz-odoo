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
