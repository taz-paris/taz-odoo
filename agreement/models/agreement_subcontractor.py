from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AgreementSubcontractor(models.Model):
    _name = "agreement.subcontractor"
    _inherit = ['mail.thread']
    _description = "Agreement Subcontractors"
    _sql_constraints = [
        ('agreement_partner_uniq', 'UNIQUE (agreement_id, partner_id)',
         "Impossible d'avoir deux DC4 pour le même sous-traitant et le même marché")
    ]

    @api.depends('agreement_id','agreement_id.name', 'partner_id', 'partner_id.name') 
    def compute_name(self):
        for rec in self:
            rec.name = "%s %s" %(rec.agreement_id.name, rec.partner_id.name)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if (rec.start_date and not rec.end_date) :
                raise ValidationError("Si la date de début est valorisée, la date de fin doit l'être également.")
            if (rec.start_date and not rec.end_date) or (rec.end_date and not rec.start_date) :
                raise ValidationError("Si la date de fin est valorisée, la date de début doit l'être également.")
            if (rec.start_date >= rec.end_date):
                raise ValidationError("La date de fin doit être strictement postérieure à la date de début.")


    name = fields.Char(compute=compute_name)
    agreement_id = fields.Many2one(
        "agreement",
        string="Accord",
        ondelete="restrict",
        # domain=[("parent_id", "=", False)],
        tracking=True,
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Sous-traitant",
        tracking=True,
        domain="[('is_company', '=', True)]",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    start_date = fields.Date(string="Date de début", tracking=True)
    end_date = fields.Date(string="Date de fin", tracking=True)
    partner_validation_date = fields.Date(string="Date de validation du DC4", tracking=True)

    currency_id = fields.Many2one(
        'res.currency',
        related="company_id.currency_id",
        # default=lambda self: self.env.company.currency_id,
        string="Currency",
        readonly=True
    )


    @api.depends('partner_id')#, 'partner_id.ref_company_ids')
    def _compute_is_partner_id_res_company(self):
        for rec in self:
            if len(rec.sudo().partner_id.ref_company_ids) != 1:
                rec.is_partner_id_res_company = False
            else :
                rec.is_partner_id_res_company = True

    def get_orders(self):
        self.ensure_one()
        if self.is_partner_id_res_company :
            order_ids = self.env['sale.order'].search([('state', '=', 'sale'), ('agreement_id', '=', self.agreement_id.id), ('company_id', '=', self.sudo().partner_id.ref_company_ids.id)])
            order_type = 'sale.order'
        else :
            order_ids = self.env['purchase.order'].search([('state', '=', 'purchase'), ('agreement_id', '=', self.agreement_id.id), ('partner_id', 'in', [self.partner_id.id])])
            order_type = 'purchase.order'
            #TODO : il faudrait également regarder tous les partner_id de la descendances du partner_id du DC4
        return order_tye, order_ids


    def get_account_moves(self):
        self.ensure_one()
        if self.is_partner_id_res_company :
            move_ids = self.env['account.move'].search([('state', '=', 'posted'), ('agreement_id', '=', self.agreement_id.id), ('company_id', '=', self.sudo().partner_id.ref_company_ids.id)])
            #   TODO : est-il nécessaire d'ajouter un filtre sur le partner_id ? => non si on controle cohérence {marché/partenaire} à la saisie de la facture et que l'on nettoie le stock
        else :
            move_ids = self.env['account_move'].search([('state', '=', 'posted'), ('agreement_id', '=', self.agreement_id.id), ('partner_id', 'in', [self.partner_id.id])])
            #TODO : il faudrait également regarder tous les partner_id de la descendances du partner_id du DC4 (ex : si un sous-traitant a plusieurs filiales ou adresses de livraison)
        return move_ids


    #TODO : ajouter contrôle pour limiter la saisie car si non on ne saura pas valoriser les montants => si aucune des entité du groupe n'est titulaire ou cotraitant du marché, le sous-traiant de niveau 1 doit forcément être une entité du groupe
    def compute(self):
        for rec in self :
            ordered_total = 0.0
            ordered_direct_payment = 0.0
            ordered_not_direct_payment = 0.0

            order_type, orders = rec.get_orders()
            for order in orders :
                for line in order.lines :
                    ordered_total += line.price_subtotal
                    if order_type == 'purchase.order' : #on ne sait pas distinguer les paiements directs lorsque Tasmane est sous-traitant
                        if line.direct_payment_purchase_order_line_id :
                            ordered_direct_payment += line.price_subtotal
                        else : 
                            ordered_not_direct_payment += line.price_subtotal


    #TODO ajouter un bouton pour afficher la liste des BCC/BCF pris en compte



    is_partner_id_res_company = fields.Boolean(compute=_compute_is_partner_id_res_company)
    max_amount = fields.Monetary("Montant HT max de sous-traitance")
    ordered_total = fields.Monetary("Total HT commandé", store=False, compute=compute)
    ordered_direct_payment = fields.Monetary("Commandé HT en paiement direct", store=False, compute=compute)
    ordered_not_direct_payment = fields.Monetary("Commandé hors paiement direct", store=False, compute=compute)
    invoiced_total = fields.Monetary("Total facturé", store=False, compute=compute)
    invoiced_direct_payment = fields.Monetary("Facturé en paiement direct", store=False, compute=compute)
    invoiced_not_direct_payment = fields.Monetary("Facturé hors paiement direct", store=False, compute=compute)



