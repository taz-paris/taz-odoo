from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta, date
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
        #_logger.info('-- RES.PARTNER get_book_by_year')
        for book_period_id in self.book_period_ids:
            if book_period_id.reference_period == str(year):
                return book_period_id.period_project_book
        return 0.0

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
    rel_partner_industry_id = fields.Many2one(related='partner_id.industry_id')
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
        'cosource_part_amount_initial',
        'cosource_part_cost_initial',
	'project_outsourcing_link_ids',
	'other_part_amount_initial',
	'other_part_cost_initial',
	'book_period_ids', 'book_employee_distribution_ids', 'book_employee_distribution_period_ids', 'book_validation_employee_id', 'book_validation_datetime',
	'accounting_closing_ids',
	'invoicing_comment',
    )
    def compute(self):
        _logger.info('====================================================================== project.py COMPUTE')
        for rec in self:
            _logger.info(str(rec.number) + "=>" +str(rec.name))
            rec.check_partners_objects_consitency() #forcer l'appel à cette fonction même si cette fonction compute n'écrit rien... car elle est appelée par les lignes de factures/sale.order/purchase.order et assure que tous ces objets liés à ce projet sont bien portés par un res.partner qui est soit le client final, soit un client intermédiaire soit un fournisseur d'un outsourcing_link
            old_default_book_end = rec.default_book_end

            rec.company_invoice_sum_move_lines, rec.company_invoice_sum_move_lines_with_tax, rec.company_paid = rec.compute_account_move_total()
            rec.company_residual = rec.company_invoice_sum_move_lines_with_tax - rec.company_paid

            rec.order_sum_sale_order_lines = rec.compute_sale_order_total(with_direct_payment=True, with_draft_sale_order=False)[0]
            rec.order_sum_sale_order_lines_with_draft = rec.compute_sale_order_total(with_direct_payment=True, with_draft_sale_order=True)[0]
            rec.order_to_invoice_company, rec.order_to_invoice_company_with_tax = rec.compute_sale_order_total(with_direct_payment=False, with_draft_sale_order=False)

   

            ######## OUTSOURCE PART
            rec.outsource_part_marging_amount_initial =  rec.outsource_part_amount_initial - rec.outsource_part_cost_initial
            if rec.outsource_part_amount_initial != 0 :                
                rec.outsource_part_marging_rate_initial = rec.outsource_part_marging_amount_initial / rec.outsource_part_amount_initial * 100
            else:
                rec.outsource_part_marging_rate_initial = 0.0 
                                                                
            outsource_part_amount_current = 0.0
            outsource_part_cost_current = 0.0
            order_to_invoice_outsourcing = 0.0
            cosource_part_amount_current = 0.0
            cosource_part_cost_current = 0.0
            outsourcing_link_purchase_order_with_draft = 0.0
            other_part_amount_current = 0.0
            other_part_cost_current = 0.0
            for link in rec.project_outsourcing_link_ids:
                link.compute()
                outsourcing_link_purchase_order_with_draft += link.compute_purchase_order_total(with_direct_payment=True, with_draft_purchase_order=True)
                if link.link_type == 'outsourcing' :
                    outsource_part_amount_current += link.outsource_part_amount_current
                    outsource_part_cost_current += link.sum_account_move_lines + link.order_direct_payment_done
                    order_to_invoice_outsourcing += link.order_direct_payment_amount
                elif link.link_type == 'cosourcing' :
                    cosource_part_amount_current += link.outsource_part_amount_current
                    cosource_part_cost_current += link.sum_account_move_lines + link.order_direct_payment_done
                    #order_to_invoice_outsourcing += link.order_direct_payment_amount
                elif link.link_type == 'other' :
                    other_part_cost_current += link.sum_account_move_lines + link.order_direct_payment_done
                    other_part_amount_current += link.outsource_part_amount_current
                else :
                    raise ValidationError(_("Type d'achat non géré : %s" % str(link.link_type)))

            rec.outsource_part_amount_current = outsource_part_amount_current
            rec.outsource_part_cost_current = outsource_part_cost_current
            rec.order_to_invoice_outsourcing = order_to_invoice_outsourcing

            rec.company_to_invoice_left = rec.order_to_invoice_company - rec.company_invoice_sum_move_lines
            rec.company_to_invoice_left_with_tax = rec.order_to_invoice_company_with_tax - rec.company_invoice_sum_move_lines_with_tax

            rec.outsource_part_marging_amount_current =  rec.outsource_part_amount_current - rec.outsource_part_cost_current
            if rec.outsource_part_amount_current != 0 :
                rec.outsource_part_marging_rate_current = rec.outsource_part_marging_amount_current / rec.outsource_part_amount_current * 100
            else :
                rec.outsource_part_marging_rate_current = 0.0 

            ######## COSOURCE PART
            rec.cosource_part_marging_amount_initial =  rec.cosource_part_amount_initial - rec.cosource_part_cost_initial
            if rec.cosource_part_amount_initial != 0 :
                rec.cosource_part_marging_rate_initial = rec.cosource_part_marging_amount_initial / rec.cosource_part_amount_initial * 100
            else:
                rec.cosource_part_marging_rate_initial = 0.0 

            rec.cosource_part_amount_current = cosource_part_amount_current
            rec.cosource_part_cost_current = cosource_part_cost_current

            rec.cosource_part_marging_amount_current =  rec.cosource_part_amount_current - rec.cosource_part_cost_current
            if rec.cosource_part_amount_current != 0 :
                rec.cosource_part_marging_rate_current = rec.cosource_part_marging_amount_current / rec.cosource_part_amount_current * 100
            else :
                rec.cosource_part_marging_rate_current = 0.0

            ######## OTHER PART
            rec.other_part_marging_amount_initial =  rec.other_part_amount_initial - rec.other_part_cost_initial
            if rec.other_part_amount_initial != 0 :
                rec.other_part_marging_rate_initial = rec.other_part_marging_amount_initial / rec.other_part_amount_initial * 100
            else:
                rec.other_part_marging_rate_initial = 0.0

            rec.other_part_cost_current = other_part_cost_current
            rec.other_part_amount_current = other_part_amount_current

            rec.other_part_marging_amount_current =  rec.other_part_amount_current - rec.other_part_cost_current
            if rec.other_part_amount_current != 0 :
                rec.other_part_marging_rate_current = rec.other_part_marging_amount_current / rec.other_part_amount_current * 100
            else:
                rec.other_part_marging_rate_current = 0.0

            ######## COMPANY PART

            rec.company_part_marging_amount_initial =  rec.company_part_amount_initial - rec.company_part_cost_initial
            if rec.company_part_amount_initial != 0 :
                rec.company_part_marging_rate_initial = rec.company_part_marging_amount_initial / rec.company_part_amount_initial * 100
            else :
                rec.company_part_marging_rate_initial = 0.0
    
            rec.company_part_amount_current = rec.order_sum_sale_order_lines_with_draft - rec.outsource_part_amount_current - rec.cosource_part_amount_current - rec.other_part_amount_current
            rec.company_part_cost_current = -rec.get_production_cost()
            rec.company_part_marging_amount_current =  rec.company_part_amount_current - rec.company_part_cost_current
            if rec.company_part_amount_current != 0 :
                rec.company_part_marging_rate_current = rec.company_part_marging_amount_current / rec.company_part_amount_current * 100
            else :
                rec.company_part_marging_rate_current = 0.0
 
            ######## TOTAL
            rec.order_amount_initial = rec.company_part_amount_initial + rec.outsource_part_amount_initial + rec.other_part_amount_initial

            rec.order_cost_initial = rec.company_part_cost_initial + rec.outsource_part_cost_initial + rec.other_part_cost_initial
            rec.order_marging_amount_initial = rec.order_amount_initial - rec.order_cost_initial
            if rec.order_amount_initial != 0 : 
                rec.order_marging_rate_initial = rec.order_marging_amount_initial / rec.order_amount_initial * 100
            else:
                rec.order_marging_rate_initial = 0.0

            rec.order_amount_current = rec.company_part_amount_current + rec.outsource_part_amount_current + rec.other_part_amount_current
            rec.order_cost_current = rec.company_part_cost_current + rec.outsource_part_cost_current + rec.other_part_cost_current
            rec.order_marging_amount_current = rec.order_amount_current - rec.order_cost_current
            if rec.order_amount_current != 0 : 
                rec.order_marging_rate_current = rec.order_marging_amount_current / rec.order_amount_current * 100
            else:
                rec.order_marging_rate_current = 0.0


            
            ######## INVOICE DATA CONTROLE
            is_consistant_prevent_napta_creation = True
            if not(rec.date) or rec.date > date(2023,1,1):
                if rec.is_prevent_napta_creation and (rec.company_part_amount_current != 0.0 or rec.company_part_cost_current != 0.0):
                    is_consistant_prevent_napta_creation = False
            rec.is_consistant_prevent_napta_creation = is_consistant_prevent_napta_creation

            is_validated_order = True
            line_ids = rec.get_sale_order_line_ids()
            for line_id in line_ids:
                line = rec.env['sale.order.line'].browse(line_id)
                if line.state in ['draft', 'sent']:
                    is_validated_order = False
                    break
            rec.is_validated_order = is_validated_order

            is_sale_order_with_draft = True
            if rec.order_sum_sale_order_lines_with_draft == 0.0 and rec.stage_id.is_part_of_booking :
                is_sale_order_with_draft = False
            rec.is_sale_order_with_draft = is_sale_order_with_draft

            is_validated_book = False
            if rec.book_validation_datetime :
                is_validated_book = True
            rec.is_validated_book = is_validated_book

            is_affected_book = True
            if not(rec.is_validated_book) and len(rec.book_employee_distribution_ids) == 0:
                is_affected_book = False
            rec.is_affected_book = is_affected_book

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

            is_outsource_part_amount_current = True
            #TODO : implémenter ce controle et et lancer recalcul sur toute la base de projets
            """
            #is_outsource_part_amount_current = fields.Boolean("Prix de revente S/T renseigné", store=True, compute=compute, help="VRAI si, pour chaque BC Fournisseur, la somme du prix de revente est > 0.")
            """
            rec.is_outsource_part_amount_current = is_outsource_part_amount_current
            
            if not(rec.number):
                rec.is_review_needed = False
            else:
                if rec.invoicing_comment or not(rec.is_validated_order) or not(rec.is_validated_purchase_order) or not(rec.is_consistant_outsourcing) or not (rec.is_consistant_prevent_napta_creation) or not(rec.is_outsource_part_amount_current) or not(rec.is_sale_order_with_draft) or not (rec.is_affected_book):
                    rec.is_review_needed = True
                else :
                    rec.is_review_needed = False

            #BOOK
            if rec.stage_is_part_of_booking :
                rec.default_book_end = rec.order_sum_sale_order_lines_with_draft - outsourcing_link_purchase_order_with_draft
            else :
                rec.default_book_end = 0.0


            if rec.is_book_manually_computed == True :
                for book_employee_distribution in rec.book_employee_distribution_ids:
                    book_employee_distribution.unlink()

            else :
                rec.book_comment = ""

                if (old_default_book_end != rec.default_book_end) and rec.stage_id.state != 'closed':
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
        self.ensure_one()
        rec = self
        line_ids = rec.get_sale_order_line_ids()
        total = 0.0
        total_with_tax = 0.0

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
            total += line.price_subtotal * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
            total_with_tax += line.price_total * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
        #_logger.info(total)
        _logger.info('----------END compute_sale_order_total')
        return total, total_with_tax
        
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
                'search_default_order' : 1,
            }
        }

        #if len(invoice_ids) == 1:
        #    action['views'] = [[False, 'form']]
        #    action['res_id'] = invoice_ids[0]

        return action


    
    def get_sale_order_line_ids(self, filter_list=[]):
        _logger.info('-- project sale.order.lines computation')
        query = self.env['sale.order.line']._search(filter_list)
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


    def get_all_customer_ids(self):
        return [self.partner_id.id] + self.partner_secondary_ids.ids

    def get_all_supplier_ids(self):
        outsourcing_link_partner_ids = []
        for link in self.project_outsourcing_link_ids :
            outsourcing_link_partner_ids.append(link.partner_id.id)
        return outsourcing_link_partner_ids
        

    def compute_account_move_total(self, filter_list=[('parent_state', 'in', ['posted'])]):
        _logger.info("--compute_account_move_total")

        all_customers = self.get_all_customer_ids()
        #TODO : ajouter une contrainte => un "client secondaire" ne peut pas avoir de outsourcing_link pour ce projet
        #TODO : ajouter une contrainte => on ne peut pas avoir une ligne de facture qui porte le compte analytic de ce projet et dont la facture est ni pour le client, ni pour un client secondaire, ni pour partener de 'outsourcing link

        line_ids = self.get_account_move_line_ids(filter_list + [('partner_id', 'in', all_customers), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('display_type', 'not in', ['line_note', 'line_section'])])
        subtotal = 0.0
        total = 0.0
        paid = 0.0
        for line_id in line_ids:
            line = self.env['account.move.line'].browse(line_id)
            subtotal += line.price_subtotal_signed * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
            total += line.price_total_signed * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
            paid += line.amount_paid * line.analytic_distribution[str(self.analytic_account_id.id)]/100.0
        return subtotal, total, paid


    def action_open_out_account_move_lines(self):
        all_customers = self.get_all_customer_ids()
        line_ids = self.get_account_move_line_ids([('partner_id', 'in', all_customers), ('move_type', 'in', ['out_refund', 'out_invoice', 'in_invoice', 'in_refund']), ('display_type', 'not in', ['line_note', 'line_section'])])

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
                'search_default_group_by_move' : 1,
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


    @api.onchange('book_validation_employee_id')
    def onchange_book_validation_employee_id(self):
        if self.book_validation_employee_id :
            self.book_validation_datetime = datetime.now()
        else :
            self.book_validation_datetime = None


    def create_sale_order(self):
        _logger.info('--- create_sale_order')
        self.ensure_one()
        
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
            }
        }


    def get_production_cost(self, filters=[]):
        production_period_amount = 0.0
        lines = self.env['account.analytic.line'].search(filters + [('project_id', '=', self.id), ('category', '=', 'project_employee_validated')])
        for line in lines :
            production_period_amount += line.amount
        return production_period_amount


    @api.constrains('partner_id', 'partner_secondary_ids', 'project_outsourcing_link_ids')
    def check_partners_consistency(self):
        for rec in self:
            if rec.partner_id.id in rec.partner_secondary_ids.ids:
                raise ValidationError(_("Le client final ne peut pas être un client intermédiaire (onglet Facturation)."))
            
            supplier_ids = rec.get_all_supplier_ids()
            if rec.partner_id.id in supplier_ids:
                raise ValidationError(_("Le client final ne peut pas être un fournisseur (onglet Achats)."))
            
            for sp in rec.partner_secondary_ids:
                if sp.id in supplier_ids:
                    raise ValidationError(_("Le client intermédiaire (onglet Facturation) ne peut pas être un fournisseur (onglet Achats)."))
            
            rec.check_partners_objects_consitency()

    def check_partners_objects_consitency(self):
        _logger.info('-- check_partners_objects_consitency')
        for rec in self:
            all_customer = rec.get_all_customer_ids()
            all_supplier = rec.get_all_supplier_ids()
            all_partner = all_customer + all_supplier

            account_move_line_ids = self.get_account_move_line_ids([('partner_id', 'not in', all_partner)])
            if len(account_move_line_ids) :
                _logger.info(all_partner)
                for line in account_move_line_ids:
                    _logger.info(self.env['account.move.line'].browse([line]).read())
                raise ValidationError(_("Enregistrement impossible pour le projet %s - %s : les écritures comptables liées à un projet doivent obligatoirement concerner soit le client final, soit le client intermédiaire (onglet Facturation), soit l'un des fourisseurs (onglet Achats) enregistrés sur la fiche du projet." % (rec.number, rec.name)))

            sale_order_line_ids = rec.get_sale_order_line_ids([('order_partner_id', 'not in', all_customer)])
            if len(sale_order_line_ids) :
                raise ValidationError(_("Enregistrement impossible pour le projet %s - %s : les bons de commande clients liées à un projet doivent obligatoirement concerner soit le client final, soit le client intermédiaire (onglet Facturation)." % (rec.number, rec.name)))
                #TODO : réduire au client final ?

            purchase_order_line_ids = self.env['project.outsourcing.link'].get_purchase_order_line_ids(filter_list=[('partner_id', 'not in', all_supplier)], analytic_account_ids=[str(rec.analytic_account_id.id)]) 
            if len(purchase_order_line_ids) :
                raise ValidationError(_("Enregistrement impossible pour le projet %s - %s : les bons de commande fournisseurs liés à un projet doivent obligatoirement concerner l'un des fournisseurs liés au projet (onglet Achat)." % (rec.number, rec.name)))

    @api.depends('accounting_closing_ids', 'accounting_closing_ids.closing_date', 'accounting_closing_ids.is_validated', 'accounting_closing_ids.pca_balance', 'accounting_closing_ids.fae_balance', 'accounting_closing_ids.fnp_balance', 'accounting_closing_ids.cca_balance')
    def compute_has_provision_running(self):
        for rec in self:
            rec.has_provision_running = False
            last_closing_sorted = rec.accounting_closing_ids.filtered(lambda r: r.is_validated==True).sorted(key=lambda r: r.closing_date, reverse=True)
            if len(last_closing_sorted):
                last_closing = last_closing_sorted[0]
                if last_closing.pca_balance or last_closing.fae_balance or last_closing.fnp_balance or last_closing.cca_balance or last_closing.production_balance :
                    rec.has_provision_running = True

    state = fields.Selection(related='stage_id.state')
    partner_id = fields.Many2one(string='Client final')
    partner_secondary_ids = fields.Many2many('res.partner', string='Clients intermediaires', help="Dans certains projet, le client final n'est pas le client facturé par Tasmane. Un client intermédie Tasmane. Enregistrer ce(s) client(s) intermédiaire(s) ici afin de permettre sa(leur) facturation pour ce projet.")
    ######## TOTAL
    order_amount_initial = fields.Monetary('Montant HT piloté par Tasmane initial', store=True, compute=compute)
    order_amount_current = fields.Monetary('Montant HT piloté par Tasmane actuel', store=True, compute=compute)
    order_sum_sale_order_lines_with_draft = fields.Monetary("Total HT commandé à Tasmane (y/c BCC à l'état Devis)", store=True, compute=compute)
    order_sum_sale_order_lines = fields.Monetary("Total HT commandé à Tasmane (uniquement à l'état BDC)", store=True, compute=compute, help="Somme des commandes passées à Tasmane par le client final ou bien le sur-traitant")

    order_cost_initial = fields.Monetary('Coût total initial', compute=compute, store=True)
    order_marging_amount_initial = fields.Monetary('Marge totale (€) initiale', compute=compute, store=True)
    order_marging_rate_initial = fields.Float('Marge totale (%) initiale', compute=compute, store=True)

    order_cost_current = fields.Monetary('Coût total actuel', compute=compute, store=True)
    order_marging_amount_current = fields.Monetary('Marge totale (€) actuelle', compute=compute, store=True)
    order_marging_rate_current = fields.Float('Marge totale (%) actuelle', compute=compute, store=True)

    order_to_invoice_company = fields.Monetary('Montant HT à facturer par Tasmane au client', compute=compute, store=True)
    order_to_invoice_company_with_tax = fields.Monetary('Montant TTC à facturer par Tasmane au client', compute=compute, store=True)
    company_invoice_sum_move_lines = fields.Monetary('Montant HT déjà facturé par Tasmane au client', compute=compute, store=True)
    company_invoice_sum_move_lines_with_tax = fields.Monetary('Montant déjà TTC facturé par Tasmane au client', compute=compute, store=True)
    company_to_invoice_left = fields.Monetary('Montant HT restant à facturer par Tasmane au client', compute=compute, store=True)
    company_to_invoice_left_with_tax = fields.Monetary('Montant TTC restant à facturer par Tasmane au client', compute=compute, store=True)
    order_to_invoice_outsourcing = fields.Monetary('Montant HT S/T paiement direct', help="Montant à facturer par les sous-traitants de Tasmane directement au client", compute=compute, store=True)

    company_paid = fields.Monetary('Montant TTC déjà payé par le client à Tasmane', compute=compute, store=True)
    company_residual = fields.Monetary('Montant TTC restant à payer par le client à Tasmane', compute=compute, store=True)

    ######## COMPANY PART
    company_part_amount_initial = fields.Monetary('Montant HT dispositif Tasmane initial', 
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

    company_part_amount_current = fields.Monetary('Montant HT dispositif Tasmane actuel', 
            compute=compute,
            store=True,
            help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_current = fields.Monetary('Coût de production dispo Tasmane (€) actuel', store=True, compute=compute, help="Montant du pointage Tasmaame valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_current = fields.Monetary('Marge sur dispo Tasmane (€) actuelle', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_current = fields.Float('Marge sur dispo Tasmane (%) actuelle', store=True, compute=compute)

    ######## OUTSOURCE PART
    outsource_part_amount_initial = fields.Monetary('Montant HT de la part sous-traitée initial', 
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

    outsource_part_amount_current = fields.Monetary('Montant HT de la part sous-traitée actuel', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte", store=True, compute=compute)
    outsource_part_cost_current = fields.Monetary('Coût de revient de la part sous-traitée actuel', store=True, compute=compute)
    outsource_part_marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', store=True, compute=compute)
    outsource_part_marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', store=True, compute=compute)

    project_outsourcing_link_ids = fields.One2many('project.outsourcing.link', 'project_id')

    ######## COSOURCE PART
    cosource_part_amount_initial = fields.Monetary('Montant HT de la part co-traitée initial', 
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            help="Montant produit par les co-traitants de Tasmane : part produite par les co-traitants")
    cosource_part_cost_initial = fields.Monetary('Coût de revient de la part co-traitée initial',
            #TODO : reactiver lorsque les DM auront initialisé les données historiques
            #states={'before_launch' : [('readonly', False)], 'launched':[('readonly', True)], 'closed':[('readonly', True)]},
            tracking=True,
            )
    cosource_part_marging_amount_initial = fields.Monetary('Marge sur part co-traitée (€) initiale', store=True, compute=compute)
    cosource_part_marging_rate_initial = fields.Float('Marge sur part co-traitée (%) initiale', store=True, compute=compute)

    cosource_part_amount_current = fields.Monetary('Montant HT de la part co-traitée actuel', help="Montant produit par les co-traitants de Tasmane : part produite par les co-traitants.", store=True, compute=compute)
    cosource_part_cost_current = fields.Monetary('Coût de revient de la part co-traitée actuel', store=True, compute=compute)
    cosource_part_marging_amount_current = fields.Monetary('Marge sur part co-traitée (€) actuelle', store=True, compute=compute)
    cosource_part_marging_rate_current = fields.Float('Marge sur part co-traitée (%) actuelle', store=True, compute=compute)



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
            compute=compute,
            store=True,
            help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_current = fields.Monetary('Coût de revient HT des autres prestations actuel', store=True, compute=compute)
    other_part_marging_amount_current = fields.Monetary('Marge sur les autres prestations (€) actuelle', store=True, compute=compute)
    other_part_marging_rate_current = fields.Float('Marge sur les autres prestations (%) actuelle', store=True, compute=compute)


    ######## BOOK
    default_book_end = fields.Monetary('Valeur du book par défaut à terminaison', store=True, compute=compute, help="Si l'étape projet est paramétrée pour compter dans le book, ce champ correspond à la valeur du book par défaut projetée à terminaison : somme des commandes clients (validées ou non) diminuée des commandes d'achats (validées ou non). Sinon ce champ a une valeur nulle.")
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
    has_provision_running = fields.Boolean('Provisions/stock prod. en cours', store=True, help="Il y a des provisions courrantes ou du stock de production au sein de la dernière cloture VALIDÉE du projet.", compute=compute_has_provision_running)


    # INVOICING MANAGEMENT DATA
    is_prevent_napta_creation = fields.Boolean("Ne pas créer sur Napta (dont portage pur)")

    is_sale_order_with_draft = fields.Boolean("BC Client existants", store=True, compute=compute, help="FAUX si le projet est en statut Accord client/Commandé/Terminé (on devrait avoir du book) mais que le total des BC client (quelque soit leur statut) est nul")
    is_validated_order = fields.Boolean("BC clients tous validés", store=True, compute=compute, help="VRAI si tous les BC clients sont à l'état 'Bon de commande'.")
    is_validated_purchase_order = fields.Boolean("BC fournisseurs tous validés", store=True, compute=compute, help="VRAI si tous les BC fournissuers sont à l'état 'Bon de commande'.")
    is_validated_book = fields.Boolean("Répartition book validée", store=True, compute=compute, help="VRAI si la répartition du book est validée.")
    is_consistant_outsourcing = fields.Boolean("BCF présents", store=True, compute=compute, help="VRAI si le type de sous-traitance est renseigné et qu'il est cohérent avec les Bons de commande fournisseur du projet.")
    is_consistant_prevent_napta_creation = fields.Boolean("Absent Napta et pas de prod. Tasmane", store=True, compute=compute, help="FAUX si la case Ne pas créer sur Napta est cochée et que le montant HT du dispositif Tasmane à date n'est pas nul.")
    is_outsource_part_amount_current = fields.Boolean("Prix de revente S/T renseigné", store=True, compute=compute, help="VRAI si, pour chaque BC Fournisseur, la somme du prix de revente est > 0.")
    is_affected_book = fields.Boolean("Book affecté", store=True, compute=compute, help="VAI si le book est validé OU qu'il existe au moins une ligne de book")

    is_review_needed = fields.Boolean('A revoir avec le DM', store=True, compute=compute, help="Projet à revoir avec le DM : au moins un contrôle est KO ou bien le champ 'Commentaire ADV' contient du texte.")
    invoicing_comment = fields.Text("Commentaire ADV")
    project_book_factor = fields.Float("Facteur de bonus/malus", default=1.0)
