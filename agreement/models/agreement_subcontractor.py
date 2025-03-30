from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AgreementSubcontractor(models.Model):
    _name = "agreement.subcontractor"
    _inherit = ['mail.thread']
    _description = "Agreement Subcontractors"
    _sql_constraints = [
        ('agreement_partner_uniq', 'UNIQUE (agreement_id, partner_id)',
         "Impossible d'avoir deux DC4 pour le même sous-traitant et le même marché")
    ]


    """
    def repprise_donnees_agreement_subcontractor(self):
        _logger.info('======== repprise_donnees_agreement_subcontractor')
        orders = self.env['purchase.order'].search([('agreement_id', '=', False)])
        for po in orders:
            if len(po.rel_project_ids) > 1 :
                _logger.info("plusieurs projets liés : ID=%s" % po.id)
            elif len(po.rel_project_ids) == 1 :
                proj = po.rel_project_ids[0]
                if proj.agreement_id  and proj.agreement_id.id not in [7] and po.partner_id.id not in [101491, 102083]:
                    _logger.info("------")
                    outsourcing_links = self.env['project.outsourcing.link'].search([('link_type', '=', 'outsourcing'), ('project_id', '=', proj.id), ('partner_id', '=', po.partner_id.id)])
                    if len(outsourcing_links) == 1 :
                        subcontractors = self.env['agreement.subcontractor'].search([('agreement_id', '=', proj.agreement_id.id), ('partner_id', '=', po.partner_id.id)])
                        if len(subcontractors) == 0 :
                            self.env['agreement.subcontractor'].create({'agreement_id' : proj.agreement_id.id, 'partner_id' : po.partner_id.id})
                            _logger.info("Création du DC4 pour l'agreement %s (ID=%s) et le sous-traitant %s (ID=%s)" % (proj.agreement_id.name, proj.agreement_id.id, po.partner_id.name, po.partner_id.id))
                        po.agreement_id = proj.agreement_id.id
                        _logger.info("Agreement %s (ID=%s) ajouté au BCF %s (ID=%s) pour le fournisseur %s (ID=%s) pour le projet %s (ID=%s)" % (proj.agreement_id.name, proj.agreement_id.id, po.name, po.id, po.partner_id.name, po.partner_id.id, proj.name, proj.id))
                    else :
                        _logger.info("Pas de project_outsourcing_link pour fournisseur %s (ID=%s) pour le projet %s (ID=%s)" % (po.partner_id.name, po.partner_id.id, proj.name, proj.id))
    """


    @api.depends('agreement_id','agreement_id.name', 'partner_id', 'partner_id.name') 
    def compute_name(self):
        for rec in self:
            rec.name = "%s %s" %(rec.agreement_id.name, rec.partner_id.name)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if (rec.start_date and not rec.end_date) :
                raise ValidationError("Si la date de début est valorisée, la date de fin doit l'être également.")
            if (rec.start_date and not rec.end_date) or (rec.end_date and not rec.start_date) :
                raise ValidationError("Si la date de fin est valorisée, la date de début doit l'être également.")
            if rec.start_date and rec.end_date and (rec.start_date >= rec.end_date):
                raise ValidationError("La date de fin doit être strictement postérieure à la date de début.")


    name = fields.Char(compute=compute_name)
    agreement_id = fields.Many2one(
        "agreement",
        string="Accord",
        ondelete="restrict",
        tracking=True,
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Sous-traitant",
        tracking=True,
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
        required=True,
    )

    start_date = fields.Date(string="Date de début", tracking=True)
    end_date = fields.Date(string="Date de fin", tracking=True)
    partner_validation_date = fields.Date(string="Date de validation du DC4", tracking=True)

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        string="Currency",
        readonly=True
    )

    code = fields.Char(string="Référence")
    comments = fields.Html('Commentaires')
    teams_link = fields.Char("Lien Teams")


    @api.depends('partner_id')#, 'partner_id.ref_company_ids')
    def _compute_is_partner_id_res_company(self):
        for rec in self:
            if rec.sudo().partner_id.ref_company_ids and rec.sudo().partner_id.ref_company_ids.so_from_po:
                rec.is_partner_id_res_company = True
            else :
                rec.is_partner_id_res_company = False

    def get_orders(self):
        self.ensure_one()
        if self.is_partner_id_res_company :#and not self.agreement_id.is_galaxy_agreement :
            order_ids = self.env['sale.order'].search([('state', '=', 'sale'), ('agreement_id', '=', self.agreement_id.id), ('company_id', 'in', [self.sudo().partner_id.ref_company_ids.id])])
            order_type = 'sale.order'
        else :
            order_ids = self.env['purchase.order'].search([('state', '=', 'purchase'), ('agreement_id', '=', self.agreement_id.id), ('partner_id', 'in', [self.partner_id.id])])
            order_type = 'purchase.order'
            #TODO : il faudrait également regarder tous les partner_id de la descendances du partner_id du DC4

        _logger.info(order_type)
        _logger.info(order_ids)
        return order_type, order_ids


    """
    def get_account_moves(self):
        self.ensure_one()
        if self.is_partner_id_res_company :
            move_ids = self.env['account.move'].search([('state', '=', 'posted'), ('agreement_id', '=', self.agreement_id.id), ('company_id', 'in', [self.sudo().partner_id.ref_company_ids.id])])
            #   TODO : est-il nécessaire d'ajouter un filtre sur le partner_id ? => non si on controle cohérence {marché/partenaire} à la saisie de la facture et que l'on nettoie le stock
        else :
            move_ids = self.env['account.move'].search([('state', '=', 'posted'), ('agreement_id', '=', self.agreement_id.id), ('partner_id', 'in', [self.partner_id.id])])
            #TODO : il faudrait également regarder tous les partner_id de la descendances du partner_id du DC4 (ex : si un sous-traitant a plusieurs filiales ou adresses de livraison)
        return move_ids
    """


    #TODO : ajouter contrôle pour limiter la saisie car si non on ne saura pas valoriser les montants => si aucune des entité du groupe n'est titulaire ou cotraitant du marché, le sous-traiant de niveau 1 doit forcément être une entité du groupe
    def compute(self):
        for rec in self :
            ordered_total = 0.0
            ordered_direct_payment = 0.0

            move_line_ids = []
            invoiced_direct_payment_validated_amount = 0.0
            order_type, orders = rec.get_orders()
            for order in orders :
                for line in order.order_line :
                    ordered_total += line.price_subtotal
                    for invoice_line in line.invoice_lines :
                        move_line_ids.append(invoice_line)
                    if order_type == 'purchase.order' : #on ne sait pas distinguer les paiements directs lorsque Tasmane est sous-traitant
                        invoiced_direct_payment_validated_amount += line.order_direct_payment_validated_amount
                        if line.direct_payment_sale_order_line_id :
                            ordered_direct_payment += line.price_subtotal
            rec.ordered_total = ordered_total
            rec.ordered_total_available = rec.max_amount - rec.ordered_total
            rec.ordered_direct_payment = ordered_direct_payment
            rec.ordered_direct_payment_available = rec.max_amount - rec.ordered_direct_payment

            rec.invoiced_direct_payment_validated_amount = invoiced_direct_payment_validated_amount

            invoiced_indirect_total = 0.0
            for move_line in move_line_ids :
                if rec.is_partner_id_res_company :
                    invoiced_indirect_total += move_line.price_subtotal_signed
                else:
                    invoiced_indirect_total += -1 * move_line.price_subtotal_signed

            rec.invoiced_total = invoiced_indirect_total + rec.invoiced_direct_payment_validated_amount
            rec.invoiced_total_available = rec.max_amount - rec.invoiced_total




    #TODO ajouter un bouton pour afficher la liste des BCC/BCF pris en compte



    is_partner_id_res_company = fields.Boolean(compute=_compute_is_partner_id_res_company)
    max_amount = fields.Monetary("Montant HT max de sous-traitance")

    markup_deal = fields.Html("Markup convenu", help="Décrire ici le taux de markup dealé avec le mandataire/co-traitant, le cas échéant")

    ordered_total = fields.Monetary("Total HT commandé", store=False, compute=compute, compute_sudo=True)
    ordered_total_available = fields.Monetary("Reste engageable sur le total HT commandé", store=False, compute=compute, compute_sudo=True)
    ordered_direct_payment = fields.Monetary("Commandé HT en paiement direct", store=False, compute=compute, compute_sudo=True)
    ordered_direct_payment_available = fields.Monetary("Reste dispo. sur le commandé HT en paiement direct", store=False, compute=compute, compute_sudo=True)

    invoiced_total = fields.Monetary("Total facturé HT", store=False, compute=compute, compute_sudo=True)
    invoiced_total_available = fields.Monetary("Reste dispo. sur total facturé HT", store=False, compute=compute, compute_sudo=True)
    invoiced_direct_payment_validated_amount = fields.Monetary("Facturé en paiement direct", store=False, compute=compute, compute_sudo=True)
    #invoiced_not_direct_payment = fields.Monetary("Facturé hors paiement direct", store=False, compute=compute, compute_sudo=True)



