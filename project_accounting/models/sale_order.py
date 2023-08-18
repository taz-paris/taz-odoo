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

    final_customer_order_amount = fields.Monetary('Montant HT du bon de commande client final', compute=compute_final_customer_order_amount, help="Montant total commandé par le client final (supérieur au montant piloté par Tasmane si Tasmane est sous-traitant. Egal au montant piloté par Tasmne sinon.)")
    other_company_amount = fields.Monetary('Montant HT de la commande piloté par un partenaire', help="Part du bon de commande du client final non piloté par Tasmane, facturé par le partneraire au client final.\nCas de cotraitraitance ou de missions dont Tasmane est lui-même sous-traitant (dans ce cas ce montant porte le markup que fait le partenaire sur la prestation Tasmane et qu'il se fera payer en direct).")

    advance_payment_ids = fields.One2many('account.payment', 'advance_sale_order_id', string="Paiements d'avance (sans facture)", help="Paiement en avance mais sans facture, notamment dans le cas de commandes publiques")


class projectAccountingSaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _sql_constraints = [
            ('direct_payment_purchase_order_line_id_uniq', 'UNIQUE (direct_payment_purchase_order_line_id)',  "Impossible d'enregistrer deux fois la même lignes de commande de SOUS-TRAITANT (purchase.order.line) dans l'attribut direct_payment_purchase_order_line_id.")
    ]



    #TODO ATTENTION :
    #  POINT PAS CLAIR : sur les sale.order et purchase.order seule la QUANTITE restant à facturer sur chaque ligne détermine si la ligne a un reliquat de facturation et en aucun cas le MONTANT
    #       Si c'est vrai, alors quand on veut facturer partiellement une ligne il faut modifier la QUANTITE sur la facture et non pas le MONTANT => Sinon la qté restant à facturer sur la SOL=0 et donc le SO passe au statut facturé, même si tout le montant n'a pas été facturé.
    #même avec les lignes ci-dessous on est bloqué dans l'assistant de création de facture, qui dit qu'il n'y a plus rien à facture... car les QTE restant à facturer sont nulles
    """
    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced', 'is_downpayment', 'untaxed_amount_to_invoice')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for line in self:
            if line.is_downpayment and line.untaxed_amount_to_invoice != 0:
                line.invoice_status = 'to invoice'
    """


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
            help = "Ligne de la commande au sous-traitant qui sera en tout ou partie payée directement par le client final et non par Tasmane",
            domain="[('id', 'in', allowed_direct_payment_purchase_order_line_ids)]",
            )

    previsional_invoice_date = fields.Date('Date prev. de facturation', states={"draft": [("readonly", False)], "sent": [("readonly", False)]})
    order_partner_invoice_id = fields.Many2one(string='Adresse de facturation', related="order_id.partner_invoice_id")
