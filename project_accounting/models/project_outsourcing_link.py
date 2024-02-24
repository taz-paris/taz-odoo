from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectOutsourcingLink(models.Model):
    _name = "project.outsourcing.link"
    _description = "Link beetwin a project and the subcontracting partner"
    _sql_constraints = [
            ('project_partner_uniq', 'UNIQUE (partner_id, project_id)',  "Impossible d'enregistrer deux fois le même sous-traitant pour un même projet. Ajoutez des commandes à la ligne existantes.")
    ]
    _check_company_auto = True

    def compute_purchase_order_total(self, with_direct_payment=True, with_draft_purchase_order=False): 
        status_list_to_keep = ['purchase']
        if with_draft_purchase_order :
            status_list_to_keep.append('draft')
        for rec in self:
            line_ids = rec.get_purchase_order_line_ids()
            total = 0.0
            for line_id in line_ids:
                line = self.env['purchase.order.line'].browse(line_id)
                if line.direct_payment_sale_order_line_id and with_direct_payment==False:
                    continue
                if line.state not in status_list_to_keep:
                    continue
                total += line.product_qty * line.price_unit * line.analytic_distribution[str(rec.project_id.analytic_account_id.id)]/100.0
            return total

    def action_open_purchase_order_lines(self):
        line_ids = self.get_purchase_order_line_ids()

        action = {
            'name': _('Lignes de BC fournisseur'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'limit' : 150,
            'groups_limit' : 150,
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
                'search_default_order_reference' : 1,
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action

    def get_purchase_order_line_ids(self, filter_list=None, analytic_account_ids=None):
        _logger.info('--get_purchase_order_line_ids')
        if filter_list == None :
            filter_list = [('partner_id', '=', self.partner_id.id)]
        if analytic_account_ids == None:
            analytic_account_ids=[str(self.project_id.analytic_account_id.id)]

        query = self.env['purchase.order.line']._search(filter_list)
        #_logger.info(query)
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', analytic_account_ids)
        query.order = None
        query_string, query_param = query.select('purchase_order_line.*')
        #_logger.info(query_string)
        #_logger.info(query_param)
        self._cr.execute(query_string, query_param)
        dic =  self._cr.dictfetchall()
        line_ids = [line.get('id') for line in dic]

        return line_ids
        

    def compute_account_move_total_outsourcing_link(self, filter_list=[('parent_state', 'in', ['posted'])]): 
        _logger.info('compute_account_move_total_outsourcing_link')
        subtotal, total, paid, lines = self.project_id.compute_account_move_total_all_partners(filter_list + [('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('partner_id', 'in', [self.partner_id.id])])
        return -1 * subtotal, -1 * total, -1 * paid


    def action_open_account_move_lines(self):
        line_ids = self.project_id.get_account_move_line_ids([('partner_id', '=', self.partner_id.id), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('display_type', 'in', ['product'])])

        action = {
            'name': _('Lignes de factures / avoirs fournisseurs'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'limit' : 150,
            'groups_limit' : 150,
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
                'search_default_group_by_move' : 1,
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action


    def create_purchase_order(self):
        _logger.info('--- create_purchase_order')
        self.ensure_one()
        

        return  {
            'res_model': 'purchase.order',
            #'res_id': order_id.id, 
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'context': {
                'create': False,
                'default_company_id' : self.company_id.id,
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
                'default_partner_id' : self.partner_id.id,
                'default_date_planned' : self.project_id.date,
                'default_previsional_invoice_date' : self.project_id.date,
                'default_user_id' : self.project_id.user_id.id,
            }
        }



    @api.depends('project_id', 'partner_id')
    def compute(self):
        _logger.info('--compute project_outsourcing_link')
        for rec in self :
            rec.outsource_part_amount_current = 0.0
            rec.order_direct_payment_amount = 0.0
            rec.order_direct_payment_done = 0.0
            rec.order_direct_payment_done_detail = ""
            purchase_lines = self.env['purchase.order.line'].browse(rec.get_purchase_order_line_ids())
            for purchase_line in purchase_lines :
                rec.outsource_part_amount_current += purchase_line.reselling_subtotal 
                if purchase_line.direct_payment_sale_order_line_id :
                    rec.order_direct_payment_amount += purchase_line.price_subtotal
                    rec.order_direct_payment_done += purchase_line.order_direct_payment_validated_amount
                    rec.order_direct_payment_done_detail += "%s \n" % (purchase_line.order_direct_payment_validated_detail or "")

            rec.order_sum_purchase_order_lines = rec.compute_purchase_order_total()
            rec.order_company_payment_amount = rec.order_sum_purchase_order_lines - rec.order_direct_payment_amount

            rec.marging_amount_current =  rec.outsource_part_amount_current - rec.order_sum_purchase_order_lines
            rec.marging_rate_current = 0.0 
            if rec.outsource_part_amount_current != 0 :
                rec.marging_rate_current = rec.marging_amount_current / rec.outsource_part_amount_current * 100

            subtotal, total, paid = rec.compute_account_move_total_outsourcing_link()
            rec.sum_account_move_lines = subtotal
            rec.sum_account_move_lines_with_tax = total
            rec.company_paid = paid
            rec.company_residual = total - paid

            rec.order_direct_payment_to_do = rec.order_direct_payment_amount - rec.order_direct_payment_done
            rec.order_company_payment_to_invoice = rec.order_company_payment_amount - rec.sum_account_move_lines


    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    partner_id = fields.Many2one('res.partner', domain="[('is_company', '=', True)]", string="Sous-traitant", required=True)
    project_id = fields.Many2one('project.project', string="Projet", required=True, check_company=True, default=_get_default_project_id, ondelete='restrict')
    link_type = fields.Selection([
            ('outsourcing', 'Sous-traitance'),
            ('cosourcing', 'Co-traitance - Cas avec validation par Tasmane des factures émises par le cotraitant vers le client'),
            ('other', 'Autres achats')
        ], string="Type d'achat", default='outsourcing')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    order_sum_purchase_order_lines = fields.Monetary('Total HT des commandes de Tasmane enregistrées', compute=compute, store=True)
    order_direct_payment_amount = fields.Monetary('Montant HT paiement direct', compute=compute, store=True, help="Montant payé directement par le client final au sous-traitant de Tasmane")
    order_company_payment_amount = fields.Monetary('Montant HT à payer à ce sous-traitant par Tasmane', help="Différence entre le total des commandes de Tasmane à ce sous-traitant pour ce projet, et le montant que le sous-traitant a prévu de facturer directement au client", compute=compute, store=True)

    sum_account_move_lines = fields.Monetary('Montant HT déjà facturé à Tasmane', help="Somme des factures envoyées par le sous-traitant à Tasmane moins la somme des avoirs dûs par Tasmane à ce sous traitant pour ce projet.", compute=compute, store=True)
    order_company_payment_to_invoice = fields.Monetary('Montant HT restant à facturer à Tasmane', compute=compute, store=True)
    sum_account_move_lines_with_tax = fields.Monetary('Montant TTC déjà facturé à Tasmane', compute=compute, store=True)

    outsource_part_amount_current = fields.Monetary('Valorisation HT de la part sous-traitée', compute=compute, store=True)
    marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', compute=compute, store=True)
    marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', compute=compute, store=True)

    order_direct_payment_done = fields.Monetary('Somme HT factures en paiement direct validées par Tasmane', compute=compute, store=True)
    order_direct_payment_done_detail = fields.Text('Détail des factures en paiement direct validées par Tasmane', compute=compute, store=True)
    order_direct_payment_to_do = fields.Monetary('Montant HT restant à valider par Tasmane', compute=compute, store=True)

    company_paid = fields.Monetary('Montant TTC déjà payé par Tasmane au S/T', compute=compute, store=True)
    company_residual = fields.Monetary('Montant TTC restant à payer par Tasmane au S/T', compute=compute, store=True)
