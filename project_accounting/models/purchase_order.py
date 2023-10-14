from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import json
import logging
_logger = logging.getLogger(__name__)



class projectAccountingPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    #TODO : 
    #   - ajouter marge globale PO
    #   - ajouter montant restant à validé sur Chorus pour paiement direct global sur PO
    #   - ajouter un statut s'il reste des factures à valider sur Chorus alors que Tasmane a payé sa part (et ajuster la liste de suivi des PO)


    def button_cancel(self):
        """
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order. You must first cancel the related vendor bills."))
        """
        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})



    @api.model_create_multi
    def create(self, vals_list):
        _logger.info('---- create purchase.order')
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        _logger.info('---- write purchase.order')
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def unlink(self):
        _logger.info('---- UNLINK purchase.order')
        old_rel_project_ids = self.rel_project_ids
        res = super().unlink()
        for project in old_rel_project_ids:
            project.compute()
        return res

    def _compute_linked_projects(self):
        for rec in self:
            for project in rec.rel_project_ids:
                project.compute()

    def comptute_project_ids(self):
        for rec in self:
            project_ids_res = []
            for line in self.order_line:
                for p in line.rel_project_ids:
                    if p.id not in project_ids_res:
                        project_ids_res.append(p.id)
            if len(project_ids_res):
                rec.rel_project_ids = [(6, 0, project_ids_res)]
            else :
                rec.rel_project_ids = False

    rel_project_ids = fields.Many2many('project.project', string="Projets", compute=comptute_project_ids)




class projectAccountingPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends('name', 'partner_ref')
    def name_get(self):
        result = []
        for pol in self:
            name = pol.name
            if pol.order_id.partner_id.name and pol.order_id.name:
                name += ' (' + pol.order_id.partner_id.name + ' / '+ pol.order_id.name + ')'
            result.append((pol.id, name))
        return result

    @api.constrains('direct_payment_sale_order_line_id', 'analytic_distribution', 'price_subtotal')
    def check(self):
        _logger.info('-- purchase.order.line CHECK')
        for rec in self:
            if rec.direct_payment_sale_order_line_id:
                if rec.analytic_distribution != rec.direct_payment_sale_order_line_id.analytic_distribution or rec.price_subtotal != rec.direct_payment_sale_order_line_id.price_subtotal:
                    raise ValidationError(_("L'une des lignes portant un paiement direct est incohérente (ex : la distribution analytique a plsuieurs compte ou bien elle n'est pas à 100%).\n\nUne fois que le paiement direct est engistré sur ligne du bon de commande du CLIENT FINAL, il n'est plus possible de modifier la distribution analytic, ni le sous-total de la ligne correspondante du BC de sous-traitance. \nVous devez supprimer le lien dans le bon de commande du client final si vous souhaitez la modifier."))


    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state', 'direct_payment_sale_order_line_id')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.direct_payment_sale_order_line_id :
                line.qty_to_invoice = 0


    @api.depends('price_subtotal', 'reselling_subtotal')
    def compute(self):
        for rec in self:
            rec.margin_amount = rec.reselling_subtotal - rec.price_subtotal
            rec.margin_rate = 0.0
            if rec.reselling_subtotal != 0 :
                rec.margin_rate = rec.margin_amount / rec.reselling_subtotal * 100


    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if line._context.get('default_analytic_distribution'):
                line.analytic_distribution = line._context.get('default_analytic_distribution')

    @api.depends('reselling_price_unit', 'product_qty')
    def _compute_reselling_subtotal(self):
        for rec in self:
            rec.reselling_subtotal = rec.reselling_price_unit * rec.product_qty

    direct_payment_sale_order_line_id = fields.One2many('sale.order.line', 'direct_payment_purchase_order_line_id',
            string="Paiement direct",
            help = "Ligne de la commande du client final")
    order_direct_payment_validated_amount = fields.Monetary('Montant HT facture paiement direct validé', help='Somme factures en paiement direct validées par Tasmane')
        #TODO : ajouter contrôles : order_direct_payment_validated_amount ne peut pas être supérieur à subtotal et doit être nul si direct_payment_sale_order_line_id = False
    order_direct_payment_validated_detail = fields.Text("Commentaire paiement direct", help='Détail des factures en paiement direct validées par Tasmane')

    previsional_invoice_date = fields.Date('Date prev. de facturation', states={"draft": [("readonly", False)], "sent": [("readonly", False)]})
    # TODO : ajouter reselling_unit_price en le prenant sur la fiche article (valeur par défaut mais modifiable) et faire la multiplication
    reselling_price_unit = fields.Float('PU HT de revente')
    reselling_subtotal = fields.Monetary('Sous-total HT de revente', compute=_compute_reselling_subtotal, help="Montant valorisé que l'on facture au client final. Somme du prix d'achat et du markup.")
    margin_amount = fields.Monetary('Marge €', compute=compute)
    margin_rate = fields.Monetary('Marge %', compute=compute)

    price_subtotal = fields.Monetary(string="Sous-total HT")
