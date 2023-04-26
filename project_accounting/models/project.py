from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class staffingProject(models.Model):
    _inherit = "project.project"
    _order = "number desc"


    #@api.model
    #def create(self, vals):
    #    if vals.get('number', '') == '':
    #            vals['number'] = self.env['ir.sequence'].next_by_code('project.project') or ''
    #    res = super().create(vals)
    #    return res

    """
    def name_get(self):
        res = []
        for rec in self:
            display_name = "%s %s (%s)" % (rec.number or "", rec.name or "", rec.partner_id.name or "")
            res.append((rec.id, display_name))
        return res

    def name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|', '|', ('number', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    """

    #inspiré de https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_timesheet/models/hr_timesheet.py#L116
    @api.depends('project_director_employee_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.project_director_employee_id.user_id if rec.project_director_employee_id else False

    def write(self, vals):
        for record in self :
            if 'stage_id' in vals.keys():
                vals['state_last_change_date'] = datetime.today()
        return super().write(vals)

    @api.model
    def create(self, vals):
        vals['state_last_change_date'] = datetime.today()
        return super().create(vals)
 
    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
    stage_is_part_of_booking = fields.Boolean()#related="stage_id.is_part_of_booking")
    partner_id = fields.Many2one(domain="[('is_company', '=', True)]")
    project_group_id = fields.Many2one('project.group', string='Groupe de projets', domain="[('partner_id', '=', partner_id)]")
        #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    project_director_employee_id = fields.Many2one('hr.employee', "Directeur de mission", default=lambda self: self.env.user.employee_id) #TODO : synchroniser cette valeur avec user_id avec un oneChange
    probability = fields.Selection([
            ('0', '0 %'),
            ('30', '30 %'),
            ('70', '70 %'),
            ('100', '100 %'),
        ], string='Probabilité')
    billed_amount = fields.Float('Montant facturé', readonly=True)
    payed_amount = fields.Float('Montant payé', readonly=True)
    state_last_change_date = fields.Date('Date de dernier changement de statut', help="Utilisé pour le filtre Nouveautés de la semaine")

    number = fields.Char('Numéro', readonly=True, required=True, copy=False, default='New')
    is_purchase_order_received = fields.Boolean('Bon de commande reçu')
    purchase_order_number = fields.Char('Numéro du bon de commande')
    remark = fields.Text("Remarques")
    outsourcing = fields.Selection([
            ('no-outsourcing', 'Sans sous-traitance'),
            ('co-sourcing', 'Avec Co-traitance'),
            ('direct-paiement-outsourcing', 'Sous-traitance paiement direct'),
            ('direct-paiement-outsourcing-company', 'Sous-traitance paiement direct + Tasmane'),
            ('outsourcing', 'Sous-traitance paiement Tasmane'),
        ], string="Type de sous-traitance")
    #TODO : ajouter un type (notamment pour les accords cadre) ? ou bien utiliser les tags ?
    #TODO : ajouter les personnes qui ont travaillé sur la propale + double book


    @api.depends('company_part_amount_initial', 'company_part_cost_initial', 'company_part_amount_current', 'company_part_cost_current', 'outsource_part_amount_initial', 'outsource_part_cost_initial', 'outsource_part_amount_current', 'outsource_part_cost_current', 'other_part_amount_initial', 'other_part_cost_initial', 'other_part_amount_current', 'other_part_cost_current')
    def compute(self):
        for rec in self:
            ######## TOTAL
            rec.order_amount = rec.company_part_amount_initial + rec.outsource_part_amount_initial + rec.other_part_amount_initial

            rec.order_cost_initial = rec.company_part_cost_initial + rec.outsource_part_cost_initial + rec.other_part_cost_initial
            rec.order_marging_amount_initial = rec.company_part_marging_amount_initial + rec.outsource_part_marging_amount_initial + rec.other_part_marging_amount_initial
            rec.order_marging_rate_initial = 0.0
            if rec.order_amount != 0 : 
                rec.order_marging_rate_initial = rec.order_marging_amount_initial / rec.order_amount * 100

            rec.order_cost_current = rec.company_part_cost_current + rec.outsource_part_cost_current + rec.other_part_cost_current
            rec.order_marging_amount_current = rec.company_part_marging_amount_current + rec.outsource_part_marging_amount_current + rec.other_part_marging_amount_current
            rec.order_marging_rate_current = 0.0
            if rec.order_amount != 0 : 
                rec.order_marging_rate_current = rec.order_marging_amount_current / rec.order_amount * 100

            ######## COMPANY PART
            rec.company_part_marging_amount_initial =  rec.company_part_amount_initial - rec.company_part_cost_initial
            rec.company_part_marging_rate_initial = 0.0
            if rec.company_part_amount_initial != 0 :
                rec.company_part_marging_rate_initial = rec.company_part_marging_amount_initial / rec.company_part_amount_initial * 100
    
            rec.company_part_marging_amount_current =  rec.company_part_amount_current - rec.company_part_cost_current
            rec.company_part_marging_rate_current = 0.0
            if rec.company_part_amount_current != 0 :
                rec.company_part_marging_rate_current = rec.company_part_marging_amount_current / rec.company_part_amount_current * 100
    
            ######## OUTSOURCE PART
            rec.outsource_part_marging_amount_initial =  rec.outsource_part_amount_initial - rec.outsource_part_cost_initial
            rec.outsource_part_marging_rate_initial = 0.0 
            if rec.outsource_part_amount_initial != 0 :                
                rec.outsource_part_marging_rate_initial = rec.outsource_part_marging_amount_initial / rec.outsource_part_amount_initial * 100
                                                                

            rec.outsource_part_amount_current = 0.0
            rec.outsource_part_cost_current = 0.0
            rec.order_to_invoice_outsourcing = 0.0
            rec.order_to_invoice_company = rec.company_part_marging_amount_current
            for link in rec.project_outsourcing_link_ids:
                rec.outsource_part_amount_current += link.outsource_part_amount_current
                rec.outsource_part_cost_current += link.sum_account_move_lines

                rec.order_to_invoice_outsourcing += link.order_direct_payment_amount
                rec.order_to_invoice_company += link.order_company_payment_amount

            rec.outsource_part_marging_amount_current =  rec.outsource_part_amount_current - rec.outsource_part_cost_current
            rec.outsource_part_marging_rate_current = 0.0 
            if rec.outsource_part_amount_current != 0 :
                rec.outsource_part_marging_rate_current = rec.outsource_part_marging_amount_current / rec.outsource_part_amount_current * 100

            ######## OTHER PART
            rec.other_part_marging_amount_initial =  rec.other_part_amount_initial - rec.other_part_cost_initial
            rec.other_part_marging_rate_initial = 0.0
            if rec.other_part_amount_initial != 0 :
                rec.other_part_marging_rate_initial = rec.other_part_marging_amount_initial / rec.other_part_amount_initial * 100

            rec.other_part_cost_current = rec.get_all_cost_current() - rec.outsource_part_cost_current

            rec.other_part_marging_amount_current =  rec.other_part_amount_current - rec.other_part_cost_current
            rec.other_part_marging_rate_current = 0.0
            if rec.other_part_amount_current != 0 :
                rec.other_part_marging_rate_current = rec.other_part_marging_amount_current / rec.other_part_amount_current * 100
            
            #BOOK
            rec.default_book = rec.company_part_amount_initial + rec.outsource_part_marging_amount_initial + rec.other_part_marging_amount_initial

    def get_all_cost_current(self):
        for rec in self:
            query = self.env['account.move.line']._search([('move_type', 'in', ['in_refund', 'in_invoice'])])
            query.add_where('analytic_distribution ? %s', [str(self.analytic_account_id.id)])
            query.order = None
            query_string, query_param = query.select('*')
            self._cr.execute(query_string, query_param)
            line_ids = [line.get('id') for line in self._cr.dictfetchall()]

            total = 0.0
            for line_id in line_ids:
                line = rec.env['account.move.line'].browse(line_id)
                #TODO : multiplier le prix_subtotal par la clé de répartition de l'analytic_distribution... même si dans notre cas ça sera toujours 100% pour le même projet
                total += line.price_subtotal

            return total

    def compute_sale_order_total(self): 
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        for rec in self:
            line_ids = rec.get_sale_order_line_ids()
            total = 0.0
            for line_id in line_ids:
                line = rec.env['sale.order.line'].browse(line_id)
                #TODO : multiplier le prix_subtotal par la clé de répartition de l'analytic_distribution... même si dans notre cas ça sera toujours 100% pour le même projet
                total += line.price_subtotal
            rec.order_sum_sale_order_lines = total


    def action_open_sale_order_lines(self):
        line_ids = self.get_sale_order_line_ids()

        action = {
            'name': _('Order lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
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
        query = self.env['sale.order.line']._search([])
        query.add_where('analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('*')
        self._cr.execute(query_string, query_param)
        line_ids = [line.get('id') for line in self._cr.dictfetchall()]

        return line_ids



    def compute_account_move_total(self): 
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        #_logger.info("--compute_account_move_total")
        for rec in self:
            #_logger.info(rec.id)
            line_ids = rec.get_account_move_line_ids()
            total = 0.0
            for line_id in line_ids:
                line = rec.env['account.move.line'].browse(line_id)
                #TODO : multiplier le prix_subtotal par la clé de répartition de l'analytic_distribution... même si dans notre cas ça sera toujours 100% pour le même projet
                total += line.price_subtotal
            #_logger.info(total)
            rec.company_invoice_sum_sale_order_lines = total
            #_logger.info("fin boucle compute_account_move_total")


    def action_open_account_move_lines(self):
        line_ids = self.get_account_move_line_ids()

        action = {
            'name': _('Invoice and refound lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            #'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env.ref("account.view_move_line_tree").id,
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
                # Si ça n'est pas égale, afficher un bandeau jaune
        move = self.env['account.move'].search([('partner_id', '=', self.partner_id.id), ('move_type', 'in', ['out_refund', 'out_invoice'])])
        move_ids = []
        for m in move :
            move_ids.append(m.id)

        query = self.env['account.move.line']._search([('move_id', 'in', move_ids)])
        _logger.info(query)
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('*')
        self._cr.execute(query_string, query_param)
        dic =  self._cr.dictfetchall()
        line_ids = [line.get('id') for line in dic]

        return line_ids


    @api.onchange('book_validation_employee_id')
    def onchange_book_validation_employee_id(self):
        if self.book_validation_employee_id :
            self.book_validation_datetime = datetime.now()
        else :
            self.book_validation_datetime = None

    final_customer_order_amount = fields.Monetary('Montant du bon de commande client final', help="Montant total commandé par le client final (supérieur au montant piloté par Tasmane si Tasmane est sous-traitant. Egal au montant piloté par Tasmne sinon.)")
    #TODO : ajouter un contrôle : le montant commandé ne peut être inférieur au montant piloté par Tasmane


    ######## TOTAL
    order_amount = fields.Monetary('Montant piloté par Tasmane (fixe ???)', store=True, compute=compute,  help="Montant à réaliser par Tasmane : dispositif Tasmane + Sous-traitance (qu'elle soit en paiment direct ou non)")
    #TODO : ajouter un contrôme opur vérifier que self.company_part_amount_initial+self.outsource_part_amount_initial == self.company_part_amount_current+self.outsource_part_amount_current
    order_sum_sale_order_lines = fields.Monetary('Total vendu par Tasmane', compute=compute_sale_order_total, help="Somme des commandes passées à Tasmane par le client final ou bien le sur-traitant")
    order_cost_initial = fields.Monetary('Coût total initial', compute=compute)
    order_marging_amount_initial = fields.Monetary('Marge totale (€) initiale', compute=compute)
    order_marging_rate_initial = fields.Float('Marge totale (%) initiale', compute=compute)

    order_cost_current = fields.Monetary('Coût total actuel', compute=compute)
    order_marging_amount_current = fields.Monetary('Marge totale (€) actuelle', compute=compute)
    order_marging_rate_current = fields.Float('Marge totale (%) actuelle', compute=compute)

    order_to_invoice_company = fields.Monetary('Montant à facturer par Tasmane', compute=compute)
    company_invoice_sum_sale_order_lines = fields.Monetary('Montant déjà facturé par Tasmane', compute=compute_account_move_total)
    order_to_invoice_outsourcing = fields.Monetary('Montant à facturer par les sous-traitants de Tasmane', compute=compute)

    ######## COMPANY PART
    company_part_amount_initial = fields.Monetary('Montant dispositif Tasmane initial', help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_initial = fields.Monetary('Coût de production dispo Tasmane (€) initial', help="Montant du pointage Tasname valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_initial = fields.Monetary('Marge sur dispo Tasmane (€) initiale', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_initial = fields.Float('Marge sur dispo Tasmane (%) initiale', store=True, compute=compute)

    company_part_amount_current = fields.Monetary('Montant dispositif Tasmane actuel', help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_current = fields.Monetary('Coût de production dispo Tasmane (€) actuel', help="Montant du pointage Tasname valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_current = fields.Monetary('Marge sur dispo Tasmane (€) actuelle', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_current = fields.Float('Marge sur dispo Tasmane (%) actuelle', store=True, compute=compute)

    ######## OUTSOURCE PART
    outsource_part_amount_initial = fields.Monetary('Montant de la part sous-traitée initial', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte")
    outsource_part_cost_initial = fields.Monetary('Coût de revient de la part sous-traitée initial')
    outsource_part_marging_amount_initial = fields.Monetary('Marge sur part sous-traitée (€) initiale', store=True, compute=compute)
    outsource_part_marging_rate_initial = fields.Float('Marge sur part sous-traitée (%) initiale', store=True, compute=compute)

    outsource_part_amount_current = fields.Monetary('Montant de la part sous-traitée actuel', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte", store=True, compute=compute)
    outsource_part_cost_current = fields.Monetary('Coût de revient de la part sous-traitée actuel', store=True, compute=compute)
    outsource_part_marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', store=True, compute=compute)
    outsource_part_marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', store=True, compute=compute)
    #quid des co-traitants

    project_outsourcing_link_ids = fields.One2many('project.outsourcing.link', 'project_id')


    ######## OTHER PART
    other_part_amount_initial = fields.Monetary('Prix de vente HT autres prestations initial', help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_initial = fields.Monetary('Coût de revient HT des autres prestations initial')
    other_part_marging_amount_initial = fields.Monetary('Marge sur les autres prestations (€) initiale', store=True, compute=compute)
    other_part_marging_rate_initial = fields.Float('Marge sur les autres prestations (%) initiale', store=True, compute=compute)

    other_part_amount_current = fields.Monetary('Prix de vente HT des autres prestations actuel', help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_current = fields.Monetary('Coût de revient HT des autres prestations actuel', store=True, compute=compute)
    other_part_marging_amount_current = fields.Monetary('Marge sur les autres prestations (€) actuelle', store=True, compute=compute)
    other_part_marging_rate_current = fields.Float('Marge sur les autres prestations (%) actuelle', store=True, compute=compute)


    default_book = fields.Monetary('Valeur du book par défaut', store=True, compute=compute, help="Somme du dispositif Tasmane prévu initialement + markup S/T prévu initialement + marge ventes autres prévue initialement")
    book_period_ids = fields.One2many('project.book_period', 'project_id', string="Book par année")
    book_employee_distribution_ids = fields.One2many('project.book_employee_distribution', 'project_id', string="Book par salarié")
    book_validation_employee_id = fields.Many2one('hr.employee', string="Book validé par")
    book_validation_datetime = fields.Datetime("Book validé le")
