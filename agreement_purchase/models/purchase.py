from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains('partner_id', 'agreement_id')
    def _check_agreement_subcontractor(self):
        for rec in self:
            link_types = []
            project_agreement_id = False
            for project in rec.rel_project_ids:
                if project.agreement_id :
                    if project_agreement_id == False :
                        project_agreement_id = project.agreement_id
                    else :
                        if project_agreement_id.id != project.agreement_id.id:
                            raise ValidationError(_("Tous les projets liés à ce BCF ne sont pas liés au même marché par défaut."))
                for link in project.outsourcing_project_link_ids :
                    if link.project_id.id == rec.partner_id.id:
                        #TODO : gérer les filliales / adresses de facturation du partner
                        link_types.append(link.link_type)
                
            if project_agreement_id and len(link_types) == 1 and link_types[0] == 'outsourcing' :
                if not rec.agreement_id:
                    raise ValidationError(_("Vous devez définir un marché car ce fournisseur est lié au projet par un lien de type Sous-traitance et que le projet est lié à un marché par défaut."))
            if project_agreement_id and len(link_types) == 1 and link_types[0] == 'other' :
                if rec.agreement_id:
                    raise ValidationError(_("Vous ne pouvez pas définir un marché sur ce BCF car le fournisseur est lié au projet avec un lien de type Autres achats."))

            if rec.agreement_id:
                subcontractors = rec.env['agreement.subcontractor'].search([('agreement_id', '=', rec.agreement_id.id), ('partner_id', '=', rec.partner_id.id)])
                #TODO : gérer les filliales / adresses de facturation du partner
                if not subcontractors:
                    raise ValidationError(_("Aucun DC4 trouvé pour ce partenaire (%s) et l'accord de ce BCF.\nVous devez en créer un." % (rec.partner_id.name)))

    @api.depends('agreement_id', 'partner_id') 
    def compute(self):
        for rec in self:
            rec.is_consistent_subcontractor_max_amount_direct_payment = True
            rec.is_consistent_subcontractor_max_amount_total = True
            subcontractors = rec.env['agreement.subcontractor'].search([('agreement_id', '=', rec.agreement_id.id), ('partner_id', '=', rec.partner_id.id)])
            if len(subcontractors) == 1 :
                sub = subcontractors[0]
                if sub.ordered_direct_payment_available < 0:
                    rec.is_consistent_subcontractor_max_amount_direct_payment = False
                if sub.ordered_total_available < 0:
                    rec.is_consistent_subcontractor_max_amount_total = False

    is_consistent_subcontractor_max_amount_direct_payment = fields.Boolean("Cohérence avec le montant max du DC4 - paiement direct", compute=compute)
    is_consistent_subcontractor_max_amount_total = fields.Boolean("Cohérence avec le montant max du DC4 - tous paiements", compute=compute)

    agreement_id = fields.Many2one(
        comodel_name="agreement",
        string="Accord cadre fournisseur",
        ondelete="restrict",
        #domain=[('domain', '=', 'purchase')],
        tracking=True,
        #readonly=True,
        check_company=False,
        copy=False,
        #states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
    )

    agreement_type_id = fields.Many2one(
        comodel_name="agreement.type",
        related="agreement_id.agreement_type_id",
        string="Type d'accord cadre fournisseur",
        ondelete="restrict",
        tracking=True,
        check_company=False,
        copy=True,
    )
