from odoo import api, fields, models, _


# Portage de ce correctif : https://github.com/odoo/odoo/commit/9304d590d882d613496bde4cb48092e5970949da#diff-1e3bd6be3bfb83a37ec9fb800ce8b1c95afe0be90ff792874ae7299c320a2f6eR1340-R1351

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_has_outstanding = fields.Boolean(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_invoice_has_outstanding',
    )

    @api.depends('invoice_outstanding_credits_debits_widget')
    def _compute_invoice_has_outstanding(self):
        for move in self:
            move.invoice_has_outstanding = bool(move.invoice_outstanding_credits_debits_widget)

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False

            if move.state not in {'draft', 'posted'} \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                ('balance', '<' if move.is_inbound() else '>', 0.0),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {
                'outstanding': True,
                'content': [],
                'move_id': move.id,
                'title': _('Outstanding credits') if move.is_inbound() else _('Outstanding debits')
            }

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if payments_widget_vals['content']:
                move.invoice_outstanding_credits_debits_widget = payments_widget_vals
