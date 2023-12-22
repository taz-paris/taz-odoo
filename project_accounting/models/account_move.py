from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)
import json


class projectAccountingAccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info('---- create account.move')
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        _logger.info('---- write account.move')
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def unlink(self):
        _logger.info('---- UNLINK account.move')
        old_rel_project_ids = self.rel_project_ids
        res = super().unlink()
        for project in old_rel_project_ids:
            project.compute()
        return res
    
    def _compute_linked_projects(self):
        for rec in self:
            for project in rec.rel_project_ids:
                project.compute()

    def action_post(self):
        if self.move_type in ['out_invoice', 'out_refund', 'out_receipt'] and not self.partner_id.external_auxiliary_code:
            raise ValidationError(_("Impossible de valider la facture/avoir client : le Code auxiliaire CEGB - Quadratus n'est pas défini sur la fiche client.")) 
        return super().action_post()

    def comptute_project_ids(self):
        for rec in self:
            project_ids_res = []
            for line in self.line_ids:
                for p in line.rel_project_ids:
                    if p.id not in project_ids_res:
                        project_ids_res.append(p.id)
            if len(project_ids_res):
                rec.rel_project_ids = [(6, 0, project_ids_res)]
            else :
                rec.rel_project_ids = False

    rel_project_ids = fields.Many2many('project.project', string="Projets", compute=comptute_project_ids)

    @api.depends('bank_partner_id')
    def _compute_partner_bank_id(self):
        super()._compute_partner_bank_id()
        for move in self:
            if move.partner_id.default_invoice_payement_bank_account:
                move.partner_bank_id = move.partner_id.default_invoice_payement_bank_account
    
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
                payments = self.env['account.payment'].search([('id', '=', line['account_payment_id'])])
                if len(payments):
                    payment = payments[0]
                    #On ne retient pas les paiements d'avance, s'ils ne concernent pas le sale.order d'au moins une des lignes de la factures
                    if payment.advance_sale_order_id and payment.advance_sale_order_id.id not in move.line_ids.sale_line_ids.order_id.ids :
                        continue
                    new_content.append(line)

            payments_widget_vals['content'] = new_content
            _logger.info(payments_widget_vals)
            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = len(new_content)


    @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_distribution')
    @api.onchange('invoice_line_ids')
    def compute_partner_list(self):
        for rec in self :
            partner_ids = []
            for l in rec.invoice_line_ids:
                for project in l.rel_project_ids :
                    for customer_id in project.get_all_customer_ids():
                        if customer_id not in partner_ids:
                            partner_ids.append(customer_id)
            rec.allowed_partner_ids = partner_ids

    allowed_partner_ids = fields.Many2many(
            'res.partner',
            compute=compute_partner_list
            )

class projectAccountingAccountMoveLine(models.Model):
    _inherit = "account.move.line"
 
    @api.depends('price_subtotal', 'direction_sign')
    def _compute_price_subtotal_signed(self):
        for rec in self:
            rec.price_subtotal_signed = rec.price_subtotal * rec.direction_sign * -1

    @api.depends('price_total', 'direction_sign')
    def _compute_price_total_signed(self):
        for rec in self:
            rec.price_total_signed = rec.price_total * rec.direction_sign * -1

    @api.depends('parent_payment_state', 'parent_state', 'move_id.amount_total', 'move_id.amount_residual', 'price_total', 'direction_sign')
    def _compute_amount_paid(self):
        _logger.info('--- _compute_amount_paid')
        for rec in self:
            if rec.parent_payment_state == 'reversed' :#or rec.parent_state != 'posted':
                #TODO : vérifier la conséquence si on supprimait la première clause : rec.parent_payment_state == 'reversed'
                #_logger.info(rec.parent_payment_state)
                #_logger.info(rec.parent_state)
                rec.amount_paid = 0.0
            else:
                #_logger.info('rec.move_id.amount_total ' + str(rec.move_id.amount_total))
                #_logger.info('rec.move_id.amount_residual ' + str(rec.move_id.amount_residual))
                #_logger.info('rec.price_total ' + str(rec.price_total))
                #_logger.info('rec.move_id.amount_total ' + str(rec.move_id.amount_total))
                invoice_amount_paid = rec.move_id.amount_total - rec.move_id.amount_residual
                rate = 1
                if rec.move_id.amount_total : 
                    rate = rec.price_total / rec.move_id.amount_total
                rec.amount_paid = invoice_amount_paid * rec.direction_sign * -1 * rate

    parent_payment_state = fields.Selection(related='move_id.payment_state', store=True, string="État du paiement (fature)")
    parent_state = fields.Selection(string="État (fature)")
    amount_paid = fields.Monetary("Montant payé", compute=_compute_amount_paid)
    #TODO : stocker la valeur de ce champ : store=True

    direction_sign = fields.Integer(related="move_id.direction_sign", store=True)
    price_subtotal_signed = fields.Monetary(
        string='Montant HT (signé)',
        compute='_compute_price_subtotal_signed',
        store=True,
        currency_field='currency_id',
    )

    price_total_signed = fields.Monetary(
        string='Montant TTC (signé)',
        compute='_compute_price_total_signed',
        store=True,
        currency_field='currency_id',
    )

    price_subtotal = fields.Monetary(string="Sous-total HT")
