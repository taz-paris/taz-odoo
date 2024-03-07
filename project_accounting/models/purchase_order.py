from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare, float_round

import json
import logging
_logger = logging.getLogger(__name__)



class projectAccountingPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    #TODO : 
    #   - ajouter marge globale PO
    #   - ajouter montant restant à validé sur Chorus pour paiement direct global sur PO
    #   - ajouter un statut s'il reste des factures à valider sur Chorus alors qu'on a payé sa part (et ajuster la liste de suivi des PO)


    def button_cancel(self):
        """
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order. You must first cancel the related vendor bills."))
        """
        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})


    def action_create_regularisation_invoice(self):
        """Create a regularisation CUSTOMER invoice associated to the PO if there are negative and received purchase.order.lines.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order.with_context(default_move_type='out_invoice')._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.price_unit >= 0 :
                    continue
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line()
                        line_vals.update({'sequence': sequence})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                        pending_section = None
                    line_vals = line._prepare_account_move_line()
                    line_vals['price_unit'] = -line_vals['price_unit']
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
            if invoice_vals['invoice_line_ids'] != []:
                invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_("Aucune ligne de ce bon de commande fournisseur n'est elligible à la création d'une facture de régularisation (ligne avec une quantité reçue > quantité facturée ET dont le prix unitaire est strictement négatif)."))

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='out_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        return self.action_view_invoice(moves)



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

    @api.onchange('margin_rate')
    def _inverse_margin_rate(self):
        for rec in self:
            if rec.margin_rate == 100 :
                #error
                pass
            else :
                rec.reselling_subtotal = (-100 * rec.price_subtotal) / (rec.margin_rate-100)
            
    @api.onchange('margin_amount')
    def _inverse_margin_amount(self):
        for rec in self : 
            rec.reselling_subtotal = rec.margin_amount + rec.price_subtotal


    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if line._context.get('default_analytic_distribution'):
                line.analytic_distribution = line._context.get('default_analytic_distribution')


    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    def _compute_qty_invoiced(self):
        #Complément nécessaire pour que les factures de régularisation (on émet une facture CLIENT vers un Fournisseur : out_invoice/out_refund) soient comptées sur les BC Fournisseurs
        #       car en natif Odoo, seuls les factures et avoirs FOURNISSEUR (in_invoice et in_refund) sont décomptés de la quantitée facturée/restant à facturée sur le BC FOURNISSEUR
        res = super()._compute_qty_invoiced()

        for line in self:
            # compute qty_invoiced
            qty_invoiced_changed = False
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel'] or inv_line.move_id.payment_state == 'invoicing_legacy':
                    if inv_line.move_id.move_type == 'out_invoice':
                        line.qty_invoiced += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        qty_invoiced_changed = True
                    elif inv_line.move_id.move_type == 'out_refund':
                        line.qty_invoiced -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        qty_invoiced_changed = True

            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done'] and qty_invoiced_changed == True :
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
                line.qty_to_invoice = 0

        return res


    @api.depends('reselling_price_unit', 'product_qty')
    def _compute_reselling_subtotal(self):
        for rec in self:
            rec.reselling_subtotal = rec.reselling_price_unit * rec.product_qty

    @api.onchange('reselling_subtotal')
    def _inverse_reselling_subtotal(self):
        for rec in self:
            if rec.product_qty != 0 :
                rec.reselling_price_unit = rec.reselling_subtotal / rec.product_qty
            else :
                rec.reselling_price_unit = 0

    @api.depends('state', 'product_uom_qty', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state not in ('purchase', 'done'):
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    invoice_status = fields.Selection(
        selection=[
            ('invoiced', "Fully Invoiced"),
            ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"),
        ],
        string="Invoice Status",
        compute='_compute_invoice_status',
        store=True
        )

    direct_payment_sale_order_line_id = fields.One2many('sale.order.line', 'direct_payment_purchase_order_line_id',
            string="Paiement direct",
            help = "Ligne de la commande du client final")
    order_direct_payment_validated_amount = fields.Monetary('Montant HT facture paiement direct validé', help='Somme factures en paiement direct validées')
        #TODO : ajouter contrôles : order_direct_payment_validated_amount ne peut pas être supérieur à subtotal et doit être nul si direct_payment_sale_order_line_id = False
    order_direct_payment_validated_detail = fields.Text("Commentaire paiement direct", help='Détail des factures en paiement direct validées')

    previsional_invoice_date = fields.Date('Date prev. de facturation', states={"draft": [("readonly", False)], "sent": [("readonly", False)]})
    # TODO : ajouter reselling_unit_price en le prenant sur la fiche article (valeur par défaut mais modifiable) et faire la multiplication
    reselling_price_unit = fields.Float('PU HT de revente')
    reselling_subtotal = fields.Monetary('Sous-total HT de revente', default=0.0, compute=_compute_reselling_subtotal, inverse=_inverse_reselling_subtotal, help="Montant valorisé que l'on facture au client final. Somme du prix d'achat et du markup.")
    margin_amount = fields.Monetary('Marge €', compute=compute, inverse=_inverse_margin_amount)
    margin_rate = fields.Float('Marge %', compute=compute, inverse=_inverse_margin_rate)

    price_subtotal = fields.Monetary(string="Sous-total HT")
