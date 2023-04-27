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

    def compute_sale_order_total(self): 
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        for rec in self:
            #rec.order_sum_sale_order_lines = 0
            line_ids = rec.get_sale_order_line_ids()
            total = 0.0
            for line_id in line_ids:
                line = self.env['purchase.order.line'].browse(line_id)
                total += line.price_subtotal
            rec.order_sum_sale_order_lines = total

    def action_open_sale_order_lines(self):
        line_ids = self.get_sale_order_line_ids()

        action = {
            'name': _('Order lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'context': {
                'create': False,
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action

    def get_sale_order_line_ids(self):
        #TODO : vérifier la cohérence entre le client du projet et le client des sale.order
            # Hypothèse structurante : un projet a toujours exactement un client
        #TODO : ajouter un contrôle pour vérifier que la somme des lignes de commande est égale au montant piloté par Tasmane (qui est lui même la somme des 3 montants dispo Tasmane/SST/frais)
                # Si ça n'est pas égale, afficher un bandeau jaune
        query = self.env['purchase.order.line']._search([('order_id.partner_id', '=', self.partner_id.id)])
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', [str(self.project_id.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('*')
        self._cr.execute(query_string, query_param)
        line_ids = [line.get('id') for line in self._cr.dictfetchall()]

        return line_ids



    def compute_account_move_total(self): 
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        for rec in self:
            line_ids = rec.get_account_move_line_ids()
            total = 0.0
            for line_id in line_ids:
                line = rec.env['account.move.line'].browse(line_id)
                #TODO : multiplier le prix_subtotal par la clé de répartition de l'analytic_distribution... même si dans notre cas ça sera toujours 100% pour le même projet
                total += line.price_subtotal
            rec.sum_account_move_lines = total

    def action_open_account_move_lines(self):
        line_ids = self.get_account_move_line_ids()

        action = {
            'name': _('Invoice and refound lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'context': {
                'create': False,
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action

    def get_account_move_line_ids(self):
        #TODO : vérifier la cohérence entre le client du projet et le client des sale.order
            # Hypothèse structurante : un projet a toujours exactement un client
        #TODO : ajouter un contrôle pour vérifier que la somme des lignes de commande est égale au montant piloté par Tasmane (qui est lui même la somme des 3 montants dispo Tasmane/SST/frais)

        move = self.env['account.move'].search([('partner_id', '=', self.partner_id.id), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund'])])
        move_ids = []
        for m in move :
            move_ids.append(m.id)

        query = self.env['account.move.line']._search([('move_id', 'in', move_ids)])
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', [str(self.project_id.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('*')
        self._cr.execute(query_string, query_param)
        line_ids = [line.get('id') for line in self._cr.dictfetchall()]

        return line_ids

    @api.depends('order_sum_sale_order_lines', 'order_direct_payment_amount', 'sum_account_move_lines')
    def compute(self):
        for rec in self :
            rec.order_company_payment_amount = rec.order_sum_sale_order_lines - rec.order_direct_payment_amount

            rec.marging_amount_current =  rec.outsource_part_amount_current - rec.sum_account_move_lines
            rec.marging_rate_current = 0.0 
            if rec.outsource_part_amount_current != 0 :
                rec.marging_rate_current = rec.marging_amount_current / rec.outsource_part_amount_current * 100


    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    partner_id = fields.Many2one('res.partner', domain="[('is_company', '=', True)]", string="Sous-traitant", required=True)
        #TODO ajouter un contrôle et un domaine => le sous-traitant d'un projet ne peut pas être égal au client final
    project_id = fields.Many2one('project.project', string="Projet", required=True, default=_get_default_project_id)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    order_sum_sale_order_lines = fields.Monetary('Total des commandes de Tasmane enregistrées', compute=compute_sale_order_total)
    order_direct_payment_amount = fields.Monetary('Montant paiement direct', help="Montant payé directement par le client final au sous-traitant de Tasmane")
        #TODO : calculer ce champ à partir d'un champ "facturé directement par" vers le res.partenr sous-traitant sur la sale.order.line 
        #TODO : il va falloir lister les factures validées sur Chorus et checker ce montant
    order_company_payment_amount = fields.Monetary('Montant à payer à ce sous-traitant par Tasmane', help="Différence entre le total des commandes de Tasmane à ce sous-traitant pour ce projet, et le montant que le sous-traitant a prévu de facturer directement au client", compute=compute)

    sum_account_move_lines = fields.Monetary('Total des factures/avoirs', help="Somme des factures envoyées par le sous-traitant à Tasmane moins la somme des avoirs dûs par Tasmane à ce sous traitant pour ce projet.", compute=compute_account_move_total)

    outsource_part_amount_current = fields.Monetary('Valorisation de la part sous-traitée')
    marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', store=True, compute=compute)
    marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', store=True, compute=compute)

    order_direct_payment_done = fields.Monetary('Somme factures en paiement direct validées par Tasmane')
    order_direct_payment_done_detail = fields.Html('Détail des factures en paiement direct validées par Tasmane')
