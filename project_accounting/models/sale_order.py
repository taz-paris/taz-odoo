from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import json
import logging
_logger = logging.getLogger(__name__)


class projectAccountingSaleOrder(models.Model):
    _inherit = "sale.order"
    _rec_name = "client_order_ref"

    client_order_ref = fields.Char(default="Pas de ref. client sur le BC")

    def compute_final_customer_order_amount(self):
        for rec in self:
            rec.final_customer_order_amount = rec.other_company_amount + rec.amount_untaxed

    final_customer_order_amount = fields.Monetary('Montant HT du bon de commande client final', compute=compute_final_customer_order_amount, help="Montant total commandé par le client final (supérieur au montant piloté si nous sommes sous-traitants. Egal au montant que nous pilotons sinon.)")
    other_company_amount = fields.Monetary('Montant HT de la commande pour le sur-traitant/co-traitant non mandataire', help="Dans le cas où nous sommes sous-traitant/co-traitant-non-mandataire d'un tiers (on ne valide pas les facture du tiers, donc ce tiers n'est pas géré comme un co-traitant), saisir ici le montant qui sera facturé par ce tiers au client final.")

    advance_payment_ids = fields.One2many('account.payment', 'advance_sale_order_id', string="Paiements d'avance (sans facture)", help="Paiement en avance mais sans facture, notamment dans le cas de commandes publiques")


    @api.model_create_multi
    def create(self, vals_list):
        _logger.info('---- create sale.order')
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        _logger.info('---- write sale.order')
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def unlink(self):
        _logger.info('---- UNLINK sale.order')
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
    target_amount = fields.Monetary("Montant cible HT - à répartir")



class projectAccountingSaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _order = "previsional_invoice_date asc"
    _sql_constraints = [
            ('direct_payment_purchase_order_line_id_uniq', 'UNIQUE (direct_payment_purchase_order_line_id)',  "Impossible d'enregistrer deux fois la même lignes de commande de SOUS-TRAITANT (purchase.order.line) dans l'attribut direct_payment_purchase_order_line_id.")
    ]



    #ATTENTION :
    #  Sur les sale.order et purchase.order seule la QUANTITE restant à facturer sur chaque ligne détermine si la ligne a un reliquat de facturation et en aucun cas le MONTANT
    #       Donc quand on veut facturer partiellement une ligne il faut modifier la QUANTITE sur la facture et non pas le MONTANT => Sinon la qté restant à facturer sur la SOL=0 et donc le SO passe au statut facturé, même si tout le montant n'a pas été facturé.
    @api.onchange('product_id')




    def _onchange_product_id_taz(self):
        if not self.product_id:
            return
        _logger.info('_onchange_product_id')
        #_logger.info(self._origin.order_id.target_amount)
        #_logger.info(self._origin.order_id.amount_untaxed)
        #_logger.info(self._origin.price_unit)
        #_logger.info(self._origin.price_subtotal)
        #_logger.info(self.order_id.target_amount)
        #_logger.info(self.order_id.amount_untaxed)
        #self.price_unit = self.order_id.target_amount - self.order_id.amount_untaxed
        total = 0.0
        for l in self.order_id.order_line:
            #if l.direct_payment_purchase_order_line_id:
            #    continue
            if l.id == self.id:
                continue
            total+=l.price_subtotal
        self.price_unit = self.order_id.target_amount - total
        _logger.info(self.price_unit)


    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        #TODO : fonction surchargée pour pré-remplir le montant de la order.line en fonction du montant total du BDC attendu
        _logger.info('_compute_price_unit')
        super()._compute_price_unit()
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            _logger.info('line')
            if line.qty_invoiced > 0:
                continue
            #total = line.order_id.amount_untaxed
            total = 0.0
            _logger.info(self.order_id.amount_untaxed)
            for l in line.order_id.order_line:
                #if l.direct_payment_purchase_order_line_id:
                #    continue
                if l.id == line.id:
                    continue
                _logger.info(l.id)
                _logger.info(line.id)
                _logger.info(l.price_subtotal)
            """
                total+=l.price_subtotal
            _logger.info(total)
            _logger.info(total-line.price_subtotal)
            _logger.info(line.price_subtotal)
            total -= line.price_subtotal
            line.price_unit = line.order_id.target_amount - total
            line.price_unit = line.price_subtotal
            """
            _logger.info(line.order_id.target_amount)
            _logger.info(line.order_id.amount_untaxed)
            line.price_unit = line.order_id.target_amount - (line.order_id.amount_untaxed -line.price_subtotal)


    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state', 'direct_payment_purchase_order_line_id')
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self:
            if line.direct_payment_purchase_order_line_id:
                line.qty_to_invoice = 0
    #TODO : ajouter un attribut permettant de suivre les PV / validation de facture des sous-traitants en paiement direct ?


    @api.constrains('direct_payment_purchase_order_line_id', 'analytic_distribution', 'price_subtotal')
    def check(self):
        for rec in self:
            if rec.direct_payment_purchase_order_line_id:
                if rec.analytic_distribution != rec.direct_payment_purchase_order_line_id.analytic_distribution :
                    raise ValidationError(_("L'une des lignes portant un paiement direct est incohérente : distribution anlytique sur SOL != POL"))
                #if rec.price_subtotal != rec.direct_payment_purchase_order_line_id.price_subtotal:
                #    raise ValidationError(_("L'une des lignes portant un paiement direct est incohérente : sous-total SOL %s != POL %s" % (rec.price_subtotal, rec.direct_payment_purchase_order_line_id.price_subtotal)))
    #TODO rec.direct_payment_purchase_order_line_id NE PEUX pas changer si la ligne a déjà été facturée et payée (line.untaxed_amount_to_invoice==0.0) ou si la ligne du purchase order a déjà été payée

    @api.depends('price_subtotal', 'analytic_distribution')
    def compute_domain_direct_payment_purchase_order_line(self_list):
        #_logger.info('---- compute_domain_direct_payment_purchase_order_line')
        for self in self_list:
            if not self.analytic_distribution :
                _logger.info('-- pas de distrib analytique')
                line_ids = []
            else:
                analytic_account_ids = list(self.analytic_distribution.keys())
                if len(analytic_account_ids) != 1 or self.analytic_distribution[analytic_account_ids[0]] != 100:
                    line_ids = []

                else :    
                    #TODO : ajouter une condition dans le filtre : le PO n'est pas annulé ni terminée et la POL n'est pas déjà facturée
                    query_string = 'SELECT * FROM "purchase_order_line" \
                                    WHERE ("purchase_order_line"."company_id" IS NULL  OR ("purchase_order_line"."company_id" in %s)) \
                                    AND  ("purchase_order_line"."id" not in (SELECT "direct_payment_purchase_order_line_id" FROM "sale_order_line" WHERE "direct_payment_purchase_order_line_id" IS NOT NULL)) \
                                    AND "purchase_order_line"."price_subtotal" = %s \
                                    AND analytic_distribution ? %s \
                                    '
                    query_param = [(1,), self.price_subtotal, str(analytic_account_ids[0])]
                    self._cr.execute(query_string, query_param)
                    line_ids = [line.get('id') for line in self._cr.dictfetchall()]
                    #_logger.info(line_ids)
        

            #_logger.info(line_ids)
            self.allowed_direct_payment_purchase_order_line_ids = line_ids


    allowed_direct_payment_purchase_order_line_ids = fields.Many2many(
            'purchase.order.line',
            compute=compute_domain_direct_payment_purchase_order_line
            )

    direct_payment_purchase_order_line_id = fields.Many2one('purchase.order.line', 
            string="Paiement direct",
            help = "Ligne de la commande au sous-traitant qui sera en tout ou partie payée directement par le client final",
            domain="[('id', 'in', allowed_direct_payment_purchase_order_line_ids)]",
            )

    previsional_invoice_date = fields.Date('Date prev. de facturation', states={"draft": [("readonly", False)], "sent": [("readonly", False)]})
    order_partner_invoice_id = fields.Many2one(string='Adresse de facturation', related="order_id.partner_invoice_id")
    qty_delivered = fields.Float(string="Qté livrée")
    comment = fields.Text("Commentaire lien ADV/facturation")
    price_subtotal = fields.Monetary(string="Sous-total HT")
    untaxed_amount_to_invoice = fields.Monetary(string="Montant HT à facturer")
    untaxed_amount_invoiced = fields.Monetary(string="Montant HT facturé")
