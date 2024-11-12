from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
from odoo import _
_logger = logging.getLogger(__name__)

import datetime
from dateutil.relativedelta import relativedelta

class projectAccountingClosing(models.Model):
    _name = "project.accounting_closing"
    _description = "Project accounting closing"
    _order = "project_id_number desc, closing_date desc"
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('project_date_uniq', 'UNIQUE (project_id, closing_date)',  "Impossible d'avoir deux clôtures à une même date pour un même projet.")
    ]
    _check_company_auto = True

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    def _get_default_closing_date(self):
        if not self.project_id and not self._get_default_project_id():
            return False

        project_id = self.project_id
        if not project_id:
            project_id = self._get_default_project_id()

        accounting_closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', project_id)], order="closing_date desc")
        if len(accounting_closing_ids) == 0 : 
            # si c'est la première cloture du projet, on met sa date de cloture par défaut au dernier jour du mois précédent le mois courant
            return datetime.date.today().replace(day=1) - datetime.timedelta(1)
        last_closing_date = accounting_closing_ids[0].closing_date
        # sinon, c'est le dernier jour du mois suivant celui de la dernière cloture
        return (last_closing_date + relativedelta(months=2)).replace(day=1) - datetime.timedelta(1)

    @api.constrains('closing_date')
    def _check_closing_date(self):
        for rec in self:
            accounting_closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', rec.project_id.id)], order="closing_date desc")
            if accounting_closing_ids[0].id != rec.id:
                raise ValidationError(_("Il n'est pas possible de saisir une date de clôture antérieure à la dernière cloture enregistrée pour ce projet."))

    @api.model_create_multi
    def create(self, vals):
        _logger.info('-- model_create_multi project_accounting_closing')
        project_ids = [val['project_id'] for val in vals]
        not_validated_closing_ids = self.env['project.accounting_closing'].search([('project_id', 'in', project_ids), ('is_validated', '=', False)])
        not_validated_closing_projects = [closing.project_id.display_name for closing in not_validated_closing_ids]
        if len(not_validated_closing_ids) >0:
            raise ValidationError(_("Il n'est pas possible de générer de nouvelles clôtures, car les projets suivants ont au moins une cloture non validée : \n%s" % (',\n'.join(not_validated_closing_projects)) ))

        closing = super().create(vals)

        for rec in closing:
            if rec.project_id:
                rec.original_stage_id = rec.project_id.stage_id.id
        return closing



    def write(self, vals):
        for rec in self :
            if rec.next_closing :
                raise ValidationError(_("Il n'est pas possible de modifier cette clôture car une clôture postérieure existe pour ce projet."))
            if rec.is_validated :
                for val_key in vals.keys():
                    if val_key not in ['is_validated', 'rel_project_stage_id', 'rel_project_user_id', 'rel_project_manager_user_id', 'name']:
                    #il faut pouvoir écrire s'il on dévalide et lorsque le projet change de statut (rel_project_stage_id est stocké pour permettre de grouper sur cet attribut)
                        raise ValidationError(_("Il n'est pas possible de modifier cette clôture car elle est validée %s (ID = %s).\n\nTentative de modification des attributs suivants, dont au moins un n'est pas modifiable une fois la clôture validée : %s." % (rec.name, rec.id, ', '.join(vals.keys()))))
        super().write(vals)


    def unlink(self):
        for rec in self:
            if rec.next_closing :
                raise ValidationError(_("Il n'est pas possible de supprimer cette clôture car une clôture postérieure existe pour ce projet."))
            if rec.is_validated :
                raise ValidationError(_("Il n'est pas possible de supprimer cette clôture car elle est validée."))
        super().unlink()



    @api.depends('project_id', 'project_id.name', 'is_validated', 'closing_date', 'pca_period_amount', 'fae_period_amount', 'cca_period_amount', 'fnp_period_amount', 'production_destocking')
    def compute(self):
        _logger.info('-- compute project_accounting_closing')
        for rec in self :

            #if rec.is_validated :
            #    continue
                #Désactivé car celà empéchait certains recalcul quand l'utilisateur cochait la case de validation et saisissait des données en même temps

            proj_id = rec.project_id #quand on applique la fonction WRITE
            if '<NewId origin=' in str(proj_id) : #pour avoir la cloture précédente et les valeur de facturation du mois lorsque l'on modifie n'importe quel attribut de la popup (c'est à dire quand on est en mon onchange)
                proj_id = rec._origin.project_id
            if not proj_id : #pour avoir les valeurs de facturation du mois dès l'ouverture de la popup de création d'une nouvelle cloture
                proj_ids = rec.env['project.project'].search([('id', '=', rec._get_default_project_id())])
                if len(proj_ids) :
                    proj_id = proj_ids[0]

            previous_accounting_closing_ids = rec.env['project.accounting_closing'].search([('project_id', '=', proj_id.id), ('closing_date', '<', rec.closing_date)], order="closing_date desc")
            previous_closing = None
            previous_closing_date_filter = []

            if len(previous_accounting_closing_ids) > 0 :
                previous_closing = previous_accounting_closing_ids[0]
                previous_closing_date_filter.append(('date', '>', previous_closing.closing_date))
            rec.previous_closing = previous_closing


            #Ces champs ne peuvent pas être de type related stored car les related stored ne sont calculés qu'après l'execution de cette fonction lors de la creation
            #   Donc celà ne permet pas de reporter correctement des provisions du mois précédent dès la création de la nouvelle cloture
            if rec.previous_closing :
                rec.pca_previous_balance = rec.previous_closing.pca_balance
                rec.fae_previous_balance = rec.previous_closing.fae_balance
                rec.cca_previous_balance = rec.previous_closing.cca_balance
                rec.fnp_previous_balance = rec.previous_closing.fnp_balance
                rec.production_previous_balance = rec.previous_closing.production_balance

            rec.invoice_period_amount = rec.get_invoice_period(proj_id, previous_closing_date_filter, rec.closing_date)[0]
            rec.purchase_period_amount = -1 * rec.get_purchase_period(proj_id, previous_closing_date_filter, rec.closing_date)[0]

            rec.pca_balance = rec.pca_previous_balance + rec.pca_period_amount
            rec.fae_balance = rec.fae_previous_balance + rec.fae_period_amount
            rec.cca_balance = rec.cca_previous_balance + rec.cca_period_amount
            rec.fnp_balance = rec.fnp_previous_balance + rec.fnp_period_amount
            rec.provision_previous_balance_sum = rec.pca_previous_balance + rec.fae_previous_balance + rec.cca_previous_balance + rec.fnp_previous_balance
            rec.provision_balance_sum = rec.pca_balance + rec.fae_balance + rec.cca_balance + rec.fnp_balance

            production_period_amount, analytic_lines = rec.get_production_period(proj_id, previous_closing_date_filter, rec.closing_date, force_recompute_amount=False)
            rec.production_period_amount = -1 * production_period_amount

            rec.production_stock = rec.production_previous_balance + rec.production_period_amount

            rec.production_balance = rec.production_stock - rec.production_destocking

            rec.gross_revenue = rec.invoice_period_amount + rec.pca_period_amount + rec.fae_period_amount
            rec.internal_revenue = rec.gross_revenue + - rec.purchase_period_amount + rec.cca_period_amount + rec.fnp_period_amount
            rec.internal_margin_amount = rec.internal_revenue - rec.production_destocking
            rec.internal_margin_rate = 0.0
            if rec.internal_revenue :
                rec.internal_margin_rate = rec.internal_margin_amount / rec.internal_revenue * 100

            rec.name  = "%s - %s" % (proj_id.name, rec.closing_date)


    def get_invoice_period(self, proj_id, previous_closing_date_filter, closing_date):
        self.ensure_one()
        return proj_id.compute_account_move_total_all_partners(previous_closing_date_filter + [('date', '<=', closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['out_refund', 'out_invoice'])])

    def get_purchase_period(self, proj_id, previous_closing_date_filter, closing_date):
        self.ensure_one()
        return proj_id.compute_account_move_total_all_partners(previous_closing_date_filter + [('date', '<=', closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['in_refund', 'in_invoice'])])

    def get_production_period(self, proj_id, previous_closing_date_filter, closing_date, force_recompute_amount):
        self.ensure_one()
        return proj_id.get_production_cost(previous_closing_date_filter+[('date', '<=', closing_date), ('category', '=', 'project_employee_validated')], force_recompute_amount=force_recompute_amount)

    def action_open_out_account_move_lines(self):
        previous_closing_date_filter = []
        if self.previous_closing : 
            previous_closing_date_filter = [('date', '>', self.previous_closing.closing_date)]
        subtotal, total, paid, line_ids = self.get_invoice_period(self.project_id, previous_closing_date_filter, self.closing_date)
        action = {
            'name': _("Lignes de factures / avoirs clients"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids), ('display_type', 'in', ['product'])],
            'view_type': 'form',
            'view_mode': 'tree',
            'target' : 'current',
            'view_id': self.env.ref("project_accounting.view_invoicelines_tree").id,
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

    def action_open_in_account_move_lines(self):
        previous_closing_date_filter = []
        if self.previous_closing : 
            previous_closing_date_filter = [('date', '>', self.previous_closing.closing_date)]
        subtotal, total, paid, line_ids = self.get_purchase_period(self.project_id, previous_closing_date_filter, self.closing_date)

        action = {
            'name': _('Lignes de factures / avoirs fournisseurs'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids), ('display_type', 'in', ['product'])],
            'view_type': 'form',
            'view_mode': 'tree',
            'target' : 'current',
            'view_id': self.env.ref("project_accounting.view_invoicelines_tree").id,
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

    def action_open_analytic_lines(self):
        production_period_amount, analytic_lines = self.get_production_period(self.project_id, [('date', '>', self.previous_closing.closing_date)], self.closing_date, force_recompute_amount=False)
        view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage du mois',
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'target': 'current',
                'domain': [('id', 'in', analytic_lines.ids)],
            }

    def goto_napta(self):
        if self.project_id.napta_id:
            return {
                'type': 'ir.actions.act_url',
                'url': 'https://app.napta.io/projects/%s?view=financial' % (self.project_id.napta_id),
                'target': 'new',
            }
        else : 
            raise ValidationError(_("Ce projet n'est lié à aucun identifiant Napta : impossible d'ouvrir sa page Napta."))

    name = fields.Char('Libellé', compute=compute, store=True)
    is_validated = fields.Boolean('Validée', tracking=True)
    comment = fields.Text("Commentaire")
    comment_previous = fields.Text("Commentaire clôture précédente", related='previous_closing.comment')
    project_id = fields.Many2one('project.project', string="Projet", required=True, check_company=True, default=_get_default_project_id, ondelete='restrict')
    project_id_number = fields.Char(related='project_id.number', store=True)
    rel_project_partner_id = fields.Many2one(related='project_id.partner_id', store=True)
    rel_project_user_id = fields.Many2one(related='project_id.user_id', store=True)
    rel_project_date_start = fields.Date(related='project_id.date_start')
    rel_project_date = fields.Date(related='project_id.date')
    rel_project_stage_id = fields.Many2one(related='project_id.stage_id', string="Statut actuel", store=True)
    rel_project_accounting_closing_ids = fields.One2many(related='project_id.accounting_closing_ids')
    rel_project_manager_user_id = fields.Many2one(related='project_id.project_manager.user_id', string="Partner ou manager en appui de l'administration du projet", help="Personne à contacter par l'ADV, capable de répondre aux aspects économiques et contractuels du projet.", store=True)
    original_stage_id = fields.Many2one('project.project.stage', readonly=True, string='Statut début clôture', help='Statut du projet à la création de la clôture ("photo")')
    closing_date = fields.Date("Date de clôture", required=False, default=_get_default_closing_date)
    previous_closing = fields.Many2one('project.accounting_closing', string="Clôture précédente", compute=compute, store=True)
    next_closing = fields.One2many('project.accounting_closing', 'previous_closing', string="Clôture suivante", readonly=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    invoice_period_amount = fields.Monetary('Facturation HT sur la période', compute=compute, store=True)
    purchase_period_amount = fields.Monetary('Achats HT sur la periode', compute=compute, store=True)
    
    pca_previous_balance = fields.Monetary('Précédent solde PCA', compute=compute, group_operator='sum', store=True)
    pca_period_amount = fields.Monetary('PCA(-)')
    pca_balance = fields.Monetary('Solde PCA', compute=compute, store=True, group_operator='sum')
    
    fae_previous_balance = fields.Monetary('Précédent solde FAE', compute=compute, group_operator='sum', store=True)
    fae_period_amount = fields.Monetary('FAE(+)')
    fae_balance = fields.Monetary('Solde FAE', compute=compute, store=True, group_operator='sum')
    
    cca_previous_balance = fields.Monetary('Précédent solde CCA', compute=compute, group_operator='sum', store=True)
    cca_period_amount = fields.Monetary('CCA(+)')
    cca_balance = fields.Monetary('Solde CCA', compute=compute, store=True, group_operator='sum')
    
    fnp_previous_balance = fields.Monetary('Précédent solde FNP', compute=compute, group_operator='sum', store=True)
    fnp_period_amount = fields.Monetary('FNP(-)')
    fnp_balance = fields.Monetary('Solde FNP', compute=compute, store=True, group_operator='sum')

    provision_previous_balance_sum = fields.Monetary('Somme reprise prov.', compute=compute, store=True, group_operator=False)
    provision_balance_sum = fields.Monetary('Somme solde prov.', compute=compute, store=True, group_operator=False)
    
    production_previous_balance = fields.Monetary('Précédent stock', compute=compute, group_operator='sum', store=True)
    production_period_amount = fields.Monetary('Production sur la période', compute=compute, store=True)
    production_stock = fields.Monetary('Stock total', compute=compute, store=True, group_operator='sum')
    production_destocking = fields.Monetary('Destockage')
    production_balance = fields.Monetary('Solde prod après destockage', compute=compute, store=True, group_operator='sum')
    
    gross_revenue = fields.Monetary('CA brut', compute=compute, store=True)
    internal_revenue = fields.Monetary('CA net de ST', compute=compute, store=True)
    internal_margin_amount = fields.Monetary('Marge nette ST (€)', compute=compute, store=True)
    internal_margin_rate = fields.Monetary('Marge nette ST (%)', compute=compute, store=True, group_operator=False)

