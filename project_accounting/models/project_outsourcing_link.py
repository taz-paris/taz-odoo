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

    def compute_purchase_order_total(self, with_direct_payment=True, with_draft_sale_order=False): 
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        status_list_to_keep = ['purchase']
        if with_draft_sale_order :
            status_list_to_keep.append('draft')
        for rec in self:
            #rec.order_sum_purchase_order_lines = 0
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
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
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
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        line_ids = self.project_id.get_account_move_line_ids(filter_list + [('partner_id', '=', self.partner_id.id), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('display_type', 'not in', ['line_note', 'line_section'])])

        subtotal = 0.0
        total = 0.0
        paid = 0.0
        for line_id in line_ids:
            line = self.env['account.move.line'].browse(line_id)
            subtotal += line.price_subtotal_signed * line.analytic_distribution[str(self.project_id.analytic_account_id.id)]/100.0
            total += line.price_total_signed * line.analytic_distribution[str(self.project_id.analytic_account_id.id)]/100.0
            paid += line.amount_paid * line.analytic_distribution[str(self.project_id.analytic_account_id.id)]/100.0 
            #vérifier que le montant est cohérent même en cas d'avoir ou si Tasmane facture un apport d'affaire à un fournisseur
        return -1 * subtotal, -1 * total, -1 * paid


    def action_open_account_move_lines(self):
        line_ids = self.project_id.get_account_move_line_ids([('partner_id', '=', self.partner_id.id), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('display_type', 'not in', ['line_note', 'line_section'])])

        action = {
            'name': _('Lignes de factures / avoirs fournisseurs'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
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
                'default_analytic_distribution': {str(self.project_id.analytic_account_id.id): 100},
                'default_partner_id' : self.partner_id.id,
                'default_date_planned' : self.project_id.date,
            }
        }



    @api.depends('project_id', 'partner_id', 'order_sum_purchase_order_lines', 'order_direct_payment_amount', 'sum_account_move_lines')
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
            rec.marging_amount_current =  rec.outsource_part_amount_current - rec.sum_account_move_lines
            rec.marging_rate_current = 0.0 
            if rec.outsource_part_amount_current != 0 :
                rec.marging_rate_current = rec.marging_amount_current / rec.outsource_part_amount_current * 100

            subtotal, total, paid = rec.compute_account_move_total_outsourcing_link()
            rec.sum_account_move_lines = subtotal
            rec.sum_account_move_lines_with_tax = total
            rec.company_paid = paid
            rec.company_residual = total - paid


    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    partner_id = fields.Many2one('res.partner', domain="[('is_company', '=', True)]", string="Sous-traitant", required=True)
        #TODO ajouter un contrôle et un domaine => le sous-traitant d'un projet ne peut pas être égal au client final
    project_id = fields.Many2one('project.project', string="Projet", required=True, default=_get_default_project_id)
    link_type = fields.Selection([
            ('outsourcing', 'Sous-traitance'),
            ('other', 'Autres achats')
        ], string="Type d'achat", default='outsourcing')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    order_sum_purchase_order_lines = fields.Monetary('Total des commandes de Tasmane enregistrées', compute=compute)
    order_direct_payment_amount = fields.Monetary('Montant paiement direct', compute=compute, help="Montant payé directement par le client final au sous-traitant de Tasmane")
        #TODO : il va falloir lister les factures validées sur Chorus et checker ce montant
    order_company_payment_amount = fields.Monetary('Montant à payer à ce sous-traitant par Tasmane', help="Différence entre le total des commandes de Tasmane à ce sous-traitant pour ce projet, et le montant que le sous-traitant a prévu de facturer directement au client", compute=compute)

    sum_account_move_lines = fields.Monetary('Montant HT déjà facturé', help="Somme des factures envoyées par le sous-traitant à Tasmane moins la somme des avoirs dûs par Tasmane à ce sous traitant pour ce projet.", compute=compute)
    sum_account_move_lines_with_tax = fields.Monetary('Montant TTC déjà facturé', compute=compute, store=True)

    outsource_part_amount_current = fields.Monetary('Valorisation de la part sous-traitée', compute=compute)
    marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', compute=compute)
    marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', compute=compute)

    order_direct_payment_done = fields.Monetary('Somme factures en paiement direct validées par Tasmane', compute=compute)
    order_direct_payment_done_detail = fields.Text('Détail des factures en paiement direct validées par Tasmane', compute=compute)

    company_paid = fields.Monetary('Montant déjà payé par Tasmane au S/T', compute=compute, store=True)
    company_residual = fields.Monetary('Montant restant à payer par Tasmane au S/T', compute=compute, store=True)
