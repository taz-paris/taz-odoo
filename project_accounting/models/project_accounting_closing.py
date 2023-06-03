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
    _order = "closing_date desc"
    _sql_constraints = [
        ('project_date_uniq', 'UNIQUE (project_id, closing_date)',  "Impossible d'avoir deux clôtures à une même date pour un même projet.")
    ]

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
            if accounting_closing_ids[0].id != self.id:
                raise ValidationError(_("Il n'est pas possible de saisir une date de clôture antérieure à la dernière cloture enregistrée."))

    def write(self, vals):
        for rec in self :
            if rec.next_closing :
                raise ValidationError(_("Il n'est pas possible de modifier cette clôture car une clôture postérieure existe."))
        super().write(vals)


    def unlink(self):
        if self.next_closing :
            raise ValidationError(_("Il n'est pas possible de supprimer cette clôture car une clôture postérieure existe."))
        super().unlink()



    @api.depends('project_id', 'closing_date', 'pca_period_amount', 'fae_period_amount', 'cca_period_amount', 'fnp_period_amount', 'production_destocking')
    def compute(self):
        _logger.info('-- compute')
        for rec in self :
            proj_id = rec.project_id #quand on applique la fonction WRITE
            if '<NewId origin=' in str(proj_id) : #pour avoir la cloture précédente et les valeur de facturation du mois lorsque l'on modifie n'importe quel attribut de la popup (c'est à dire quand on est en mon onchange)
                proj_id = rec._origin.project_id
            if not proj_id : #pour avoir les valeurs de facturation du mois dès l'ouverture de la popup de création d'une nouvelle cloture
                proj_id = rec.env['project.project'].search([('id', '=', rec._get_default_project_id())])[0]

            previous_accounting_closing_ids = rec.env['project.accounting_closing'].search([('project_id', '=', proj_id.id), ('closing_date', '<', rec.closing_date)], order="closing_date desc")
            previous_closing = None
            previous_closing_date_filter = []

            if len(previous_accounting_closing_ids) > 0 :
                previous_closing = previous_accounting_closing_ids[0]
                previous_closing_date_filter.append(('date', '>', previous_closing.closing_date))
            rec.previous_closing = previous_closing


            rec.invoice_period_amount = rec.project_id.compute_account_move_total(previous_closing_date_filter + [('date', '<=', rec.closing_date)])
            rec.invoice_balance = rec.invoice_previous_balance + rec.invoice_period_amount

            rec.purchase_period_amount = rec.project_id.get_all_cost_current(previous_closing_date_filter + [('date', '<=', rec.closing_date)])
            rec.purchase_balance = rec.purchase_previous_balance + rec.purchase_period_amount

            rec.pca_balance = rec.pca_previous_balance + rec.pca_period_amount
            rec.fae_balance = rec.fae_previous_balance + rec.fae_period_amount
            rec.cca_balance = rec.cca_previous_balance + rec.cca_period_amount
            rec.fnp_balance = rec.fnp_previous_balance + rec.fnp_period_amount
            rec.provision_previous_balance_sum = rec.pca_previous_balance + rec.fae_previous_balance + rec.cca_previous_balance + rec.fnp_previous_balance
            rec.provision_balance_sum = rec.pca_balance + rec.fae_balance + rec.cca_balance + rec.fnp_balance

            production_period_amount = 0.0
            lines = self.env['account.analytic.line'].search(previous_closing_date_filter + [('project_id', '=', proj_id.id), ('date', '<=', rec.closing_date)])
            for line in lines :
                production_period_amount += line.amount
            rec.production_period_amount = production_period_amount

            rec.production_stock = rec.production_previous_balance + rec.production_period_amount
            rec.production_balance = rec.production_stock - rec.production_destocking

            rec.gross_revenue = rec.invoice_period_amount + rec.pca_period_amount + rec.fae_period_amount
            rec.internal_revenue = rec.gross_revenue - rec.purchase_balance + rec.cca_period_amount + rec.fnp_period_amount
            rec.internal_margin_amount = rec.internal_revenue - rec.production_destocking
            rec.internal_margin_rate = 0.0
            if rec.internal_revenue :
                rec.internal_margin_rate = rec.internal_margin_amount / rec.internal_revenue * 100

            rec.name  = "%s - %s" % (proj_id.name, rec.closing_date)

    name = fields.Char('Libellé', compute=compute, store=True)
    project_id = fields.Many2one('project.project', string="Projet", required=True, default=_get_default_project_id, ondelete='cascade')
    closing_date = fields.Date("Date de clôture", required=True, default=_get_default_closing_date)
    previous_closing = fields.Many2one('project.accounting_closing', string="Clôture précédente", compute=compute, store=True)
    next_closing = fields.One2many('project.accounting_closing', 'previous_closing', string="Clôture suivante", readonly=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    invoice_previous_balance = fields.Monetary('Précédent solde facturation', related='previous_closing.invoice_balance')
    invoice_period_amount = fields.Monetary('Facturation du mois', compute=compute, store=True)
    invoice_balance = fields.Monetary('Solde de facturation', compute=compute, store=True)
    
    purchase_previous_balance = fields.Monetary('Précédent solde achats', related='previous_closing.purchase_balance')
    purchase_period_amount = fields.Monetary('Achats du mois', compute=compute, store=True)
    purchase_balance = fields.Monetary('Solde d\'achats', compute=compute, store=True)
    
    pca_previous_balance = fields.Monetary('Précédent solde PCA', related='previous_closing.pca_balance')
    pca_period_amount = fields.Monetary('PCA(-)')
    pca_balance = fields.Monetary('Solde PCA', compute=compute, store=True)
    
    fae_previous_balance = fields.Monetary('Précédent solde FAE', related='previous_closing.fae_balance')
    fae_period_amount = fields.Monetary('FAE(+)')
    fae_balance = fields.Monetary('Solde FAE', compute=compute, store=True)
    
    cca_previous_balance = fields.Monetary('Précédent solde CCA', related='previous_closing.cca_balance')
    cca_period_amount = fields.Monetary('CCA(+)')
    cca_balance = fields.Monetary('Solde CCA', compute=compute, store=True)
    
    fnp_previous_balance = fields.Monetary('Précédent solde FNP', related='previous_closing.fnp_balance')
    fnp_period_amount = fields.Monetary('FNP(-)')
    fnp_balance = fields.Monetary('Solde FNP', compute=compute, store=True)

    provision_previous_balance_sum = fields.Monetary('Somme reprise prov.', compute=compute, store=True)
    provision_balance_sum = fields.Monetary('Somme solde prov.', compute=compute, store=True)
    
    production_previous_balance = fields.Monetary('Précédent stock', related='previous_closing.production_balance')
    production_period_amount = fields.Monetary('Production du mois', compute=compute, store=True)
    production_stock = fields.Monetary('Stock total', compute=compute, store=True)
    production_destocking = fields.Monetary('Destockage')
    production_balance = fields.Monetary('Solde prod après destockage', compute=compute, store=True)
    
    gross_revenue = fields.Monetary('CA brut', compute=compute, store=True)
    internal_revenue = fields.Monetary('CA net de ST', compute=compute, store=True)
    internal_margin_amount = fields.Monetary('Marge nette ST (€)', compute=compute, store=True)
    internal_margin_rate = fields.Monetary('Marge nette ST (%)', compute=compute, store=True)
