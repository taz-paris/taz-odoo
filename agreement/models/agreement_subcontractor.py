from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AgreementSubcontractor(models.Model):
    _name = "agreement.subcontractor"
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

    parent_subcontractor_agreement_id = fields.Many2one(
        "agreement.subcontractor",
        string="Fiche DC4 parente",
        help="Permet de chaîner les sous-traitances de niveau N. Vide si sous-traitant de niveau 1.",
        tracking=True,
        domain="[('agreement_id', '=', agreement_id)]",
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
    max_amount = fields.Monetary("Montant max de sous-traitance", store=True)



