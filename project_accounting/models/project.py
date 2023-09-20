from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta
import json

import logging
_logger = logging.getLogger(__name__)


class projectAccountProject(models.Model):
    _inherit = "project.project"
    _order = "number desc"
    _sql_constraints = [
        ('number_uniq', 'UNIQUE (number)',  "Impossible d'enregistrer deux projets avec le même numéro.")
    ]

    @api.model_create_multi
    def create(self, vals_list):
        #_logger.info('---- MULTI create project from accounting_project')
        projects = self.browse()
        for vals in vals_list:
            vals['number'] = self.env['ir.sequence'].next_by_code('project.project') or ''
            vals['state_last_change_date'] = datetime.today()
            #_logger.info('Numéro de projet auto : %s' % str(vals['number']))
            projects |= super().create(vals)
        return projects

    def name_get(self):
        res = []
        for rec in self:
            display_name = "%s %s" % (rec.number or "", rec.name or "")
            if rec.partner_id : 
                display_name += "("+str(rec.partner_id.name)+")"
            res.append((rec.id, display_name))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if name :
            args += ['|', ('name', operator, name), ('number', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


    def get_book_by_year(self, year):
        _logger.info('-- RES.PARTNER get_book_by_year')
        res = 0.0
        for book_period_id in self.book_period_ids:
            if book_period_id.reference_period == str(year):
                res += book_period_id.period_project_book
                #TODO : ne pas sommer les book pas encore validés ???
        #_logger.info(res)
        return res

    #inspiré de https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_timesheet/models/hr_timesheet.py#L116
    @api.depends('project_director_employee_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.project_director_employee_id.user_id if rec.project_director_employee_id else False

    def write(self, vals):
        #_logger.info('----- projet WRITE')
        #_logger.info(vals)
        for record in self :
            if 'stage_id' in vals.keys():
                vals['state_last_change_date'] = datetime.today()
        return super().write(vals)

    @api.depends('project_director_employee_id')
    def _compute_user_enrolled_ids(self):
        #surchargée dans le module staffing
        for rec in self:
            user_enrolled_ids = []
            if rec.user_id :
                user_enrolled_ids.append(rec.user_id.id)
            rec.user_enrolled_ids = [(6, 0, user_enrolled_ids)]

    user_enrolled_ids = fields.Many2many('res.users', string="Utilisateurs concernés par ce projet", compute=_compute_user_enrolled_ids, store=True)

    state_last_change_date = fields.Date('Date de dernier changement de statut', help="Utilisé pour le filtre Nouveautés de la semaine")
    color_rel = fields.Selection(related="stage_id.color", store=True)
    number = fields.Char('Numéro', readonly=True, required=False, copy=False, default='')
    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
    stage_is_part_of_booking = fields.Boolean(related="stage_id.is_part_of_booking")
    partner_id = fields.Many2one(domain="[('is_company', '=', True)]")
    project_group_id = fields.Many2one('project.group', string='Groupe de projets', domain="[('partner_id', '=', partner_id)]")
        #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    project_director_employee_id = fields.Many2one('hr.employee', "Directeur de mission", default=lambda self: self.env.user.employee_id) #TODO : synchroniser cette valeur avec user_id avec un oneChange
    user_id = fields.Many2one(compute=_compute_user_id, store=True)
    probability = fields.Selection([
            ('0', '0 %'),
            ('30', '30 %'),
            ('70', '70 %'),
            ('100', '100 %'),
        ], string='Probabilité')
    remark = fields.Text("Remarques")

    amount = fields.Float('Montant net S/T Fitnet', readonly=True) #Attribut temporaire Fitnet à supprimer
    billed_amount = fields.Float('Montant facturé Fitnet', readonly=True) #Attribut temporaire Fitnet à supprimer
    payed_amount = fields.Float('Montant payé Fitnet', readonly=True) #Attribut temporaire Fitnet à supprime
    is_purchase_order_received = fields.Boolean('Bon de commande reçu Fitnet', readonly=True) #Attribut temporaire Fitnet à supprimer
    purchase_order_number = fields.Char('Numéro du bon de commande Fitnet', readonly=True) #Attribut temporaire Fitnet à supprimer (le numéro de BC est sur le bon de commande client et non sur le projet en cible)
    outsourcing = fields.Selection([
            ('no-outsourcing', 'Sans sous-traitance'),
            ('co-sourcing', 'Avec Co-traitance'),
            ('direct-paiement-outsourcing', 'Sous-traitance paiement direct'),
            ('direct-paiement-outsourcing-company', 'Sous-traitance paiement direct + Tasmane'),
            ('outsourcing', 'Sous-traitance paiement Tasmane'),
        ], string="Type de sous-traitance") #Attribut temporaire Fitnet à supprimer
    agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="Marché par défaut sur les BC clients",
        ondelete="restrict",
        tracking=True,
        readonly=False,
        copy=False,
    ) #Attribut temporaire Fitnet à supprimer (l'agreement_id est sur le bon de commande client et non sur le projet en cible)


    #le modèle analytic_mixin est surchargé dans ce module project_accounting afin d'appeller cette fonction compute lorsqu'une ligne avec une distribution analytque liée à ce projet est créée/modifiée
    @api.depends(
	'state',
	'company_part_amount_initial',
	'company_part_cost_initial',
        'outsource_part_amount_initial',
        'outsource_part_cost_initial',
	'project_outsourcing_link_ids',
	'other_part_amount_initial',
	'other_part_cost_initial',
	'company_part_amount_current',
	'other_part_amount_current',
	'book_period_ids', 'book_employee_distribution_ids', 'book_employee_distribution_period_ids', 'book_validation_employee_id', 'book_validation_datetime',
	'accounting_closing_ids',
	'invoicing_comment',
    )
    def compute(self):
        _logger.info('====================================================================== project.py COMPUTE')
        for rec in self:
            _logger.info(str(rec.number) + "=>" +str(rec.name))
            old_default_book_initial = rec.default_book_initial
            old_default_book_current = rec.default_book_current
            old_default_book_end = rec.default_book_end

            rec.company_invoice_sum_move_lines = rec.compute_account_move_total()

            ######## TOTAL
            rec.order_amount_initial = rec.company_part_amount_initial + rec.outsource_part_amount_initial + rec.other_part_amount_initial
            rec.order_amount_current = rec.company_part_amount_current + rec.outsource_part_amount_current + rec.other_part_amount_current

            rec.order_cost_initial = rec.company_part_cost_initial + rec.outsource_part_cost_initial + rec.other_part_cost_initial
            rec.order_marging_amount_initial = rec.company_part_marging_amount_initial + rec.outsource_part_marging_amount_initial + rec.other_part_marging_amount_initial
            rec.order_marging_rate_initial = 0.0
            if rec.order_amount_initial != 0 : 
                rec.order_marging_rate_initial = rec.order_marging_amount_initial / rec.order_amount_initial * 100

            rec.order_cost_current = rec.company_part_cost_current + rec.outsource_part_cost_current + rec.other_part_cost_current
            rec.order_marging_amount_current = rec.company_invoice_sum_move_lines - rec.order_cost_current
            rec.order_marging_rate_current = 0.0
            if rec.company_invoice_sum_move_lines != 0 : 
                rec.order_marging_rate_current = rec.order_marging_amount_current / rec.company_invoice_sum_move_lines * 100

            ######## COMPANY PART

            rec.company_part_marging_amount_initial =  rec.company_part_amount_initial - rec.company_part_cost_initial
            if rec.company_part_amount_initial != 0 :
                rec.company_part_marging_rate_initial = rec.company_part_marging_amount_initial / rec.company_part_amount_initial * 100
            else :
                rec.company_part_marging_rate_initial = 0.0
    
            rec.company_part_cost_current = -rec.get_production_cost()
            rec.company_part_marging_amount_current =  rec.company_part_amount_current - rec.company_part_cost_current
            if rec.company_part_amount_current != 0 :
                rec.company_part_marging_rate_current = rec.company_part_marging_amount_current / rec.company_part_amount_current * 100
            else :
                rec.company_part_marging_rate_current = 0.0
    

            ######## OUTSOURCE PART
            rec.outsource_part_marging_amount_initial =  rec.outsource_part_amount_initial - rec.outsource_part_cost_initial
            if rec.outsource_part_amount_initial != 0 :                
                rec.outsource_part_marging_rate_initial = rec.outsource_part_marging_amount_initial / rec.outsource_part_amount_initial * 100
            else:
                rec.outsource_part_marging_rate_initial = 0.0 
                                                                

            rec.outsource_part_amount_current = 0.0
            rec.outsource_part_cost_current = 0.0
            rec.order_to_invoice_outsourcing = 0.0
            rec.order_sum_sale_order_lines = rec.compute_sale_order_total()
            rec.order_to_invoice_company = rec.compute_sale_order_total(with_direct_payment=False)
            outsourcing_link_purchase_order_with_draft = 0.0
            for link in rec.project_outsourcing_link_ids:
                rec.outsource_part_amount_current += link.outsource_part_amount_current
                rec.outsource_part_cost_current += link.sum_account_move_lines
                rec.order_to_invoice_outsourcing += link.order_direct_payment_amount
                outsourcing_link_purchase_order_with_draft += link.compute_purchase_order_total(with_direct_payment=True, with_draft_sale_order=True)
                    #TODO : plutot lire le paiement direct sur le sale.order... ça sera plus fialble si on a pas créer le outsourcing_link

            rec.company_to_invoice_left = rec.order_to_invoice_company - rec.company_invoice_sum_move_lines

            rec.outsource_part_marging_amount_current =  rec.outsource_part_amount_current - rec.outsource_part_cost_current
            if rec.outsource_part_amount_current != 0 :
                rec.outsource_part_marging_rate_current = rec.outsource_part_marging_amount_current / rec.outsource_part_amount_current * 100
            else :
                rec.outsource_part_marging_rate_current = 0.0 

            ######## OTHER PART
            rec.other_part_marging_amount_initial =  rec.other_part_amount_initial - rec.other_part_cost_initial
            if rec.other_part_amount_initial != 0 :
                rec.other_part_marging_rate_initial = rec.other_part_marging_amount_initial / rec.other_part_amount_initial * 100
            else:
                rec.other_part_marging_rate_initial = 0.0

            rec.other_part_cost_current = rec.get_all_cost_current() - rec.outsource_part_cost_current

            rec.other_part_marging_amount_current =  rec.other_part_amount_current - rec.other_part_cost_current
            if rec.other_part_amount_current != 0 :
                rec.other_part_marging_rate_current = rec.other_part_marging_amount_current / rec.other_part_amount_current * 100
            else:
                rec.other_part_marging_rate_current = 0.0
            
            ######## INVOICE DATA CONTROLE
            #TODO : il ne faut regarder que les commandes pour lesquelles on a effectivement reçu un numéro de commande... pas les commandes en brouillon
            is_constistant_order_amount = True
            if rec.order_amount_current != rec.order_sum_sale_order_lines :
                is_constistant_order_amount = False
            rec.is_constistant_order_amount = is_constistant_order_amount

            is_validated_order = True
            line_ids = rec.get_sale_order_line_ids()
            for line_id in line_ids:
                line = rec.env['sale.order.line'].browse(line_id)
                if line.state in ['draft', 'sent']:
                    is_validated_order = False
                    break
            rec.is_validated_order = is_validated_order

            is_validated_book = False
            if rec.book_validation_datetime :
                is_validated_book = True
            rec.is_validated_book = is_validated_book

            is_consistant_outsourcing = True
            if not(rec.outsourcing):
                is_consistant_outsourcing = False
            else :
                if rec.outsourcing in ['direct-paiement-outsourcing', 'direct-paiement-outsourcing-company', 'outsourcing']:
                    if rec.outsource_part_amount_current == 0:
                         is_consistant_outsourcing = False
            rec.is_consistant_outsourcing = is_consistant_outsourcing

            is_validated_purchase_order = True
            #TODO : à débuger et lancer le recalcul sur toute la base de projets
            """
            for link in rec.project_outsourcing_link_ids:
                for purchase_order_line in link.get_purchase_order_line_ids():
                    line = rec.env['purchase.order.line'].browse(line_id)
                    if line.state in ['draft', 'sent', 'to approve']:
                        is_validated_purchase_order = False
                        break
            """
            rec.is_validated_purchase_order = is_validated_purchase_order

            if rec.invoicing_comment or not(rec.is_constistant_order_amount) or not(rec.is_validated_order) or not(rec.is_validated_purchase_order) or not(rec.is_validated_book) or not(rec.is_consistant_outsourcing):
                rec.is_review_needed = True
            else :
                rec.is_review_needed = False

            #BOOK
            rec.default_book_initial = rec.company_part_amount_initial + rec.outsource_part_marging_amount_initial + rec.other_part_marging_amount_initial
            rec.default_book_current = rec.company_part_amount_current + rec.outsource_part_marging_amount_current + rec.other_part_marging_amount_current
            rec.default_book_end = rec.compute_sale_order_total(with_direct_payment=True, with_draft_sale_order=True) - outsourcing_link_purchase_order_with_draft
            #if rec.default_book_initial != rec.default_book_current and ((old_default_book_initial != rec.default_book_initial) or (old_default_book_current != rec.default_book_current)):
            #    rec.book_validation_employee_id = False
            #    rec.book_validation_datetime = False


            if rec.is_book_manually_computed == True :
                for book_employee_distribution in rec.book_employee_distribution_ids:
                    book_employee_distribution.unlink()

            else :
                rec.book_comment = ""

                """
                generer_book_2023 = False
                if rec.number != False and rec.number[0:2] == '23':
                    generer_book_2023 = True
                else :
                    for book_period in rec.book_period_ids:
                        if int(book_period.reference_period) == 2022 :
                            generer_book_2023 = True
                            break

                if generer_book_2023:
                """

                if (old_default_book_end != rec.default_book_end) and rec.stage_id.state != 'closed':
                #if True:
                    #on modifie le montant de l'année en cours
                    t = datetime.today()
                    current_year = t.year
                    book_period_current_year = False
                    pasted_years_book = 0.0
                    for book_period in rec.book_period_ids:
                        if int(book_period.reference_period) == current_year :
                            book_period_current_year = book_period
                        elif int(book_period.reference_period) < current_year :
                            pasted_years_book += book_period.period_project_book
                        elif int(book_period.reference_period) > current_year :
                            book_period.unlink()
                    default_current_year_book_amount = rec.default_book_end - pasted_years_book
                    if book_period_current_year == False :
                        dic = {
                                'project_id' : rec._origin.id,
                                'reference_period' : str(current_year),
                            }
                        book_period_current_year = rec.env['project.book_period'].create(dic)

                    if book_period_current_year.period_project_book != default_current_year_book_amount:
                        book_period_current_year.period_project_book = default_current_year_book_amount
                        rec.book_validation_employee_id = False
                        rec.book_validation_datetime = False

                    #TODO : provque une erreur "Enregistrement inexistant ou supprimé.(Enregistrement : project.book_period(380,), Utilisateur : 2) "
                    #if book_period_current_year.period_project_book == 0.0 :
                    #    book_period_current_year.unlink()


    def compute_sale_order_total(self, with_direct_payment=True, with_draft_sale_order=False): 
        _logger.info('----------compute_sale_order_total => with_direct_payment=' + str(with_direct_payment))
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        self.ensure_one()
        rec = self
        # avec un utilisateur avec un ID != celui d'aurélien, ça crash :
        #       Record does not exist or has been deleted
        #       (Record: sale.order.line(1,), Field : sale.order.line.price_subtotal, User: 2) 
        # renvoyé par sudo vim /usr/lib/python3/dist-packages/odoo/fields.py ligne 1191
        line_ids = rec.get_sale_order_line_ids()
        total = 0.0

        status_list_to_keep = ['sale']
        if with_draft_sale_order :
            status_list_to_keep.append('draft')
        for line_id in line_ids:
            line = rec.env['sale.order.line'].browse(line_id)
            #_logger.info(line.read())
            if line.direct_payment_purchase_order_line_id and with_direct_payment==False :
                continue
            if line.state not in status_list_to_keep:
                continue
            total += line.product_uom_qty * line.price_unit * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
        #_logger.info(total)
        _logger.info('----------END compute_sale_order_total')
        return total
        
    def action_open_sale_order_lines(self):
        line_ids = self.get_sale_order_line_ids()

        action = {
            'name': _('Lignes de commande client'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'target' : 'current',
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action


    
    def get_sale_order_line_ids(self):
        _logger.info('-- project sale.order.lines computation')
        query = self.env['sale.order.line']._search([])
        #_logger.info(query)
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('sale_order_line.*') #important car Odoo fait un LEFT join obligatoire, donc si on fait SELECT * on a plusieurs colonne ID dans le résultat
        #_logger.info(query_string)
        #_logger.info(query_param)
        self._cr.execute(query_string, query_param)
        dic =  self._cr.dictfetchall()
        line_ids = [line.get('id') for line in dic]
        #_logger.info(line_ids)
        return line_ids


    def get_all_cost_current(self, filter_list=[]):
        #TODO : changer de logique : avoir une fonction qui retourne les lignes de vente qui ne sont pas déjà attribuées à un sous-traitant puis sommer à partir de ces ID de lignes
            # et ajouter un bouton pour voir le détail des lignes affectées
        _logger.info("--get_all_cost_current")
        for rec in self :
            line_ids = rec.get_account_move_line_ids(filter_list + [('move_type', 'in', ['in_refund', 'in_invoice'])])
            total = 0.0
            #_logger.info(len(line_ids))
            for line_id in line_ids:
                line = rec.env['account.move.line'].browse(line_id)
                if str(rec.analytic_account_id.id) in line.analytic_distribution.keys():
                    total += line.price_subtotal_signed * line.analytic_distribution[str(rec.analytic_account_id.id)]/100.0
            #_logger.info(total)
            return total


    def compute_account_move_total(self, filter_list=[('parent_state', 'in', ['posted'])]):
        #TODO : gérer les statuts du sale.order => ne prendre que les lignes des sale.order validés ?
        _logger.info("--compute_account_move_total")
        line_ids = self.get_account_move_line_ids(filter_list + [('move_type', 'in', ['out_refund', 'out_invoice']), ('display_type', 'not in', ['line_note', 'line_section'])])
            #On ne met pas le partenr_id dans le filtre car dans certains cas, Tasmane ne facture pas le client final, mais un intermédiaire (Sopra par exemple) 
        total = 0.0
        #_logger.info(len(line_ids))
        for line_id in line_ids:
            line = self.env['account.move.line'].browse(line_id)
            total += line.price_subtotal_signed * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
        #_logger.info(total)
        return total


    def action_open_out_account_move_lines(self):
        line_ids = self.get_account_move_line_ids([('move_type', 'in', ['out_refund', 'out_invoice'])])
            #On ne met pas le partenr_id dans le filtre car dans certains cas, Tasmane ne facture pas le client final, mais un intermédiaire (Sopra par exemple) 
            #TODO : on devrait exlure les sous-traitants mais intégrer in_refund, out_invoice.. mais dans ce cas ça mélangerait les factures de frais généraux...

        action = {
            'name': _("Lignes de factures / avoirs"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            #'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids)],
            'view_type': 'form',
            'view_mode': 'tree',
            'target' : 'current',
            'view_id': self.env.ref("project_accounting.view_invoicelines_tree").id,
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
                'default_move_type' : 'out_invoice',
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action

    def action_open_all_account_move_lines(self):
        line_ids = self.get_account_move_line_ids()
            #On ne met pas le partenr_id dans le filtre car dans certains cas, Tasmane ne facture pas le client final, mais un intermédiaire (Sopra par exemple) 
            #TODO : on devrait exlure les sous-traitants mais intégrer in_refund, out_invoice.. mais dans ce cas ça mélangerait les factures de frais généraux...

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
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action


    def get_account_move_line_ids(self, filter_list=[]):
        _logger.info('--get_account_move_line_ids')
        query = self.env['account.move.line']._search(filter_list)
        #_logger.info(query)
        if query == []:
            return []
        query.add_where('analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query.order = None
        query_string, query_param = query.select('account_move_line.*')
        #_logger.info(query_string)
        #_logger.info(query_param)
        self._cr.execute(query_string, query_param)
        dic =  self._cr.dictfetchall()
        line_ids = [line.get('id') for line in dic]
        #_logger.info(line_ids)

        return line_ids


    @api.onchange('book_validation_employee_id')
    def onchange_book_validation_employee_id(self):
        if self.book_validation_employee_id :
            self.book_validation_datetime = datetime.now()
        else :
            self.book_validation_datetime = None


    def create_sale_order(self):
        _logger.info('--- create_sale_order')
        self.ensure_one()
        
        price_unit = 0.0
        #TODO : déduire le montant des sale order en état draft ?
        if self.order_amount_current - self.order_sum_sale_order_lines > 0:
            price_unit = self.order_amount_current - self.order_sum_sale_order_lines

        return  {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'context': {
                'create': False,
                'default_partner_id' : self.partner_id.id,
                'default_agreement_id' : self.agreement_id.id,
                'default_user_id' : self.user_id.id,
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
                'default_previsional_invoice_date' : self.date,
                #'default_price_unit' : price_unit,
                'default_target_amount' : price_unit,
            }
        }


    def get_production_cost(self, filters=[]):
        production_period_amount = 0.0
        lines = self.env['account.analytic.line'].search(filters + [('project_id', '=', self.id), ('category', '=', 'project_employee_validated')])
        for line in lines :
            production_period_amount += line.amount
        return production_period_amount


    @api.onchange('company_part_amount_initial', 'company_part_cost_initial', 'other_part_amount_initial')
    def copy_initial_current(self):
        for rec in self :
            #if rec.stage_id.state == 'before_launch':
            rec.company_part_amount_current = rec.company_part_amount_initial
            rec.company_part_cost_current = rec.company_part_cost_initial
            rec.other_part_amount_current = rec.other_part_amount_initial


    state = fields.Selection(related='stage_id.state')
    ######## TOTAL
    order_amount_initial = fields.Monetary('Montant piloté par Tasmane initial', store=True, compute=compute,  help="Montant à réaliser par Tasmane initial : dispositif Tasmane + Sous-traitance (qu'elle soit en paiment direct ou non)")
    order_amount_current = fields.Monetary('Montant piloté par Tasmane actuel', store=True, compute=compute,  help="Montant à réaliser par Tasmane actuel : dispositif Tasmane + Sous-traitance (qu'elle soit en paiment direct ou non)")
    order_sum_sale_order_lines = fields.Monetary('Total commandé à Tasmane', store=True, compute=compute, help="Somme des commandes passées à Tasmane par le client final ou bien le sur-traitant")

    order_cost_initial = fields.Monetary('Coût total initial', compute=compute, store=True)
    order_marging_amount_initial = fields.Monetary('Marge totale (€) initiale', compute=compute, store=True)
    order_marging_rate_initial = fields.Float('Marge totale (%) initiale', compute=compute, store=True)

    order_cost_current = fields.Monetary('Coût total actuel', compute=compute, store=True)
    order_marging_amount_current = fields.Monetary('Marge totale (€) actuelle', compute=compute, store=True)
    order_marging_rate_current = fields.Float('Marge totale (%) actuelle', compute=compute, store=True)

    order_to_invoice_company = fields.Monetary('Montant à facturer par Tasmane au client', compute=compute, store=True)
    company_invoice_sum_move_lines = fields.Monetary('Montant déjà facturé par Tasmane au client', compute=compute, store=True)
    company_to_invoice_left = fields.Monetary('Montant restant à factuer par Tasmane au client', compute=compute, store=True)
    order_to_invoice_outsourcing = fields.Monetary('Montant S/T paiement direct', help="Montant à facturer par les sous-traitants de Tasmane directement au client", compute=compute, store=True)

    ######## COMPANY PART
    company_part_amount_initial = fields.Monetary('Montant dispositif Tasmane initial', 
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_initial = fields.Monetary('Coût de production dispo Tasmane (€) initial', 
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Montant du pointage Tasmane valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_initial = fields.Monetary('Marge sur dispo Tasmane (€) initiale', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_initial = fields.Float('Marge sur dispo Tasmane (%) initiale', store=True, compute=compute)

    company_part_amount_current = fields.Monetary('Montant dispositif Tasmane actuel', 
            states={'before_launch' : [('readonly', True)], 'launched':[('readonly', False)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_current = fields.Monetary('Coût de production dispo Tasmane (€) actuel', store=True, compute=compute, help="Montant du pointage Tasmaame valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    #company_part_cost_current = fields.Monetary('Coût de production dispo Tasmane (€) actuel', 
    #        states={'before_launch' : [('readonly', True)], 'launched':[('readonly', False)], 'closed':[('readonly', True)]},
    #        help="Montant du pointage Tasmane valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_current = fields.Monetary('Marge sur dispo Tasmane (€) actuelle', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_current = fields.Float('Marge sur dispo Tasmane (%) actuelle', store=True, compute=compute)

    ######## OUTSOURCE PART
    outsource_part_amount_initial = fields.Monetary('Montant de la part sous-traitée initial', 
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte")
    outsource_part_cost_initial = fields.Monetary('Coût de revient de la part sous-traitée initial',
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            )
    outsource_part_marging_amount_initial = fields.Monetary('Marge sur part sous-traitée (€) initiale', store=True, compute=compute)
    outsource_part_marging_rate_initial = fields.Float('Marge sur part sous-traitée (%) initiale', store=True, compute=compute)

    outsource_part_amount_current = fields.Monetary('Montant de la part sous-traitée actuel', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte", store=True, compute=compute)
    outsource_part_cost_current = fields.Monetary('Coût de revient de la part sous-traitée actuel', store=True, compute=compute)
    outsource_part_marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', store=True, compute=compute)
    outsource_part_marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', store=True, compute=compute)
    #quid des co-traitants

    project_outsourcing_link_ids = fields.One2many('project.outsourcing.link', 'project_id')


    ######## OTHER PART
    other_part_amount_initial = fields.Monetary('Montant HT de la part "autres prestations" initial', 
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_initial = fields.Monetary('Coût de revient HT des autres prestations initial',
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            )
    other_part_marging_amount_initial = fields.Monetary('Marge sur les autres prestations (€) initiale', store=True, compute=compute)
    other_part_marging_rate_initial = fields.Float('Marge sur les autres prestations (%) initiale', store=True, compute=compute)

    other_part_amount_current = fields.Monetary('Montant HT de la part "autres prestations" actuel', 
            states={'before_launch' : [('readonly', True)], 'launched':[('readonly', False)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_current = fields.Monetary('Coût de revient HT des autres prestations actuel', store=True, compute=compute)
    other_part_marging_amount_current = fields.Monetary('Marge sur les autres prestations (€) actuelle', store=True, compute=compute)
    other_part_marging_rate_current = fields.Float('Marge sur les autres prestations (%) actuelle', store=True, compute=compute)


    ######## BOOK
    default_book_initial = fields.Monetary('Valeur du book par défaut initial', store=True, compute=compute, help="Somme du dispositif Tasmane prévu initialement + markup S/T prévu initialement + marge ventes autres prévue initialement")
    default_book_current = fields.Monetary('Valeur du book par défaut actuel', store=True, compute=compute, help="Valeur du book par défaut actualisée suivant les commandes/factures/avoirs effectivement reçus")
    default_book_end = fields.Monetary('Valeur du book par défaut à terminaison', store=True, compute=compute, help="Valeur du book par défaut projetée à terminaison : somme des commandes clients (validées ou non) diminuée des commandes d'achats (validées ou non)")
    is_book_manually_computed = fields.Boolean('Book géré manuellement')
    book_comment = fields.Text('Commentaire sur le book')
    book_period_ids = fields.One2many('project.book_period', 'project_id', string="Book par année")
    book_employee_distribution_ids = fields.One2many('project.book_employee_distribution', 'project_id', string="Book par salarié")
    book_employee_distribution_period_ids = fields.One2many('project.book_employee_distribution_period', 'project_id', 'Book par salarié et par an')
    book_validation_employee_id = fields.Many2one('hr.employee', string="Book validé par", tracking=True)
        #TODO : il faudrait que seul le groupe TAZ_management puisse modifier le champ book_validation_employee_id, mais en attendant on log les changements dans le chatter.
    book_validation_datetime = fields.Datetime("Book validé le", tracking=True)


    # ACCOUNTING CLOSING
    accounting_closing_ids = fields.One2many('project.accounting_closing', 'project_id', 'Clôtures comptables')


    # INVOICING MANAGEMENT DATA
    is_constistant_order_amount = fields.Boolean('Cohérence commande client/ventilation mission', store=True, compute=compute, help="Faux lorsque le montant total des lignes de commandes est différent de la somme de la part Dispositifi Tasmane+part sous-traitée+part autres prestations")
    is_validated_order = fields.Boolean("BC clients tous validés", store=True, compute=compute, help="VRAI si tous les BC clients sont à l'état 'Bon de commande'.")
    is_validated_purchase_order = fields.Boolean("BC fournisseurs tous validés", store=True, compute=compute, help="VRAI si tous les BC fournissuers sont à l'état 'Bon de commande'.")
    is_validated_book = fields.Boolean("Répartition book validée", store=True, compute=compute, help="VRAI si la répartition du book est validée.")
    is_consistant_outsourcing = fields.Boolean("BCF présents", store=True, compute=compute, help="VRAI si le type de sous-traitance est renseigné et qu'il est cohérent avec les Bons de commande fournisseur du projet.")
    is_review_needed = fields.Boolean('A revoir avec le DM', store=True, compute=compute, help="Projet à revoir avec le DM : au moins un contrôle est KO ou bien le champ 'Commentaire ADV' contient du texte.")
    invoicing_comment = fields.Text("Commentaire ADV")
