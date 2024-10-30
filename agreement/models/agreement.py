# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models


class Agreement(models.Model):
    _name = "agreement"
    _description = "Agreement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True


    code = fields.Char(required=True, tracking=True)
    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Pouvoir adjudicateur",
        ondelete="restrict",
        #domain=[("parent_id", "=", False)],
        tracking=True,
    )

    partner_company_ids = fields.Many2many(
        "res.partner",
        relation="agreement_partner_company_ids",
        string="Donneur d'ordres",
        tracking=True,
        domain="[('is_company', '=', True)]",
    )

    partner_principal_id = fields.Many2one(
        "res.partner",
        string="Mandataire",
        tracking=True,
        domain="[('is_company', '=', True)]",
    )

    partner_cocontractor_ids = fields.Many2many(
        "res.partner",
        relation="agreement_cocontractors_company_ids",
        string="Co-traitant",
        tracking=True,
        domain="[('is_company', '=', True)]",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    is_template = fields.Boolean(
        string="Is a Template?",
        default=False,
        copy=False,
        help="Set if the agreement is a template. "
        "Template agreements don't require a partner.",
    )
    agreement_type_id = fields.Many2one(
        "agreement.type",
        string="Agreement Type",
        help="Select the type of agreement",
    )

    domain = fields.Selection(
        "_domain_selection",
        string="Domain",
        default="sale",
        tracking=True,
    )

    agreement_subcontractor_ids = fields.One2many(
        comodel_name="agreement.subcontractor",
        inverse_name="agreement_id",
        string="Sous-traitants",
    )

    active = fields.Boolean(default=True)
    signature_date = fields.Date(tracking=True)
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(string="Date limite de commande", tracking=True)
    end_date_contractors = fields.Date(string="Date de fin d'exécution des prestataires", tracking=True)

    comments = fields.Html('Commentaires')
    referent = fields.Many2one("res.users", string="Référent")
    teams_link = fields.Char("Lien Teams")

    currency_id = fields.Many2one(
        'res.currency',
        related="company_id.currency_id",
        # default=lambda self: self.env.company.currency_id,
        string="Currency",
        readonly=True
    )
    max_amount = fields.Monetary("Montant max de l'accord", store=True)
    other_contractors_total_sale_order = fields.Monetary("Montant commandé auprès des co-traitants")

    @api.model
    def _domain_selection(self):
        return [
            ("sale", _("Sale")),
            ("purchase", _("Purchase")),
        ]

    @api.onchange("agreement_type_id")
    def agreement_type_change(self):
        if self.agreement_type_id and self.agreement_type_id.domain:
            self.domain = self.agreement_type_id.domain

    def name_get(self):
        res = []
        for agr in self:
            name = agr.name
            if agr.code:
                name = "[{}] {}".format(agr.code, agr.name)
            res.append((agr.id, name))
        return res

    _sql_constraints = [
        (
            "code_partner_company_unique",
            "unique(code, partner_id, company_id)",
            "This agreement code already exists for this partner!",
        )
    ]

    def copy(self, default=None):
        """Always assign a value for code because is required"""
        default = dict(default or {})
        if default.get("code", False):
            return super().copy(default)
        default.setdefault("code", _("%s (copy)") % (self.code))
        return super().copy(default)
