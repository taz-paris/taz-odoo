# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
import datetime
import logging
_logger = logging.getLogger(__name__)

class Agreement(models.Model):
    _name = "agreement"
    _description = "Agreement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            #if (rec.start_date and not rec.end_date) :
            #    raise ValidationError("Si la date de début est valorisée, la date de fin doit l'être également.")
            #if (rec.start_date and not rec.end_date) or (rec.end_date and not rec.start_date) :
            #    raise ValidationError("Si la date de fin est valorisée, la date de début doit l'être également.")
            if rec.start_date and rec.end_date and (rec.start_date >= rec.end_date):
                raise ValidationError("La date de fin doit être strictement postérieure à la date de début.")

    def compute(self):
        for rec in self :
            is_galaxy_agreement = False
            if rec.mandator_id.ref_company_ids:
                is_galaxy_agreement = True
            for cocontractor in rec.cocontractor_ids:
                if cocontractor.ref_company_ids:
                    is_galaxy_agreement = True
                    break
            rec.is_galaxy_agreement = is_galaxy_agreement

            today = datetime.date.today()
            if rec.end_date and (today > rec.end_date) :
                    rec.passed_time_rate = 100
            elif rec.start_date and (today < rec.start_date):
                    rec.passed_time_rate = 0
            else :
                if rec.start_date and rec.end_date :
                    total_days_period = rec.end_date - rec.start_date
                    passed_time = today - rec.start_date
                    rec.passed_time_rate = passed_time / total_days_period * 100.0
                else : 
                    rec.passed_time_rate = 0

    code = fields.Char(required=False, tracking=True)
    name = fields.Char(required=True, tracking=True)

    state = fields.Selection([('new', "DCE publié"),
                              ('nogo', "NoGo galaxie"),
                              ('work_on_anwser', "Go - Réponse en cours"),
                              ('lost', "Marché perdu"),
                              ('won', "Marché en cours"),
                              ('passed', "Marché terminé"),
                              ('cancelled', "Annulé - erreur Tasmane"),
                              ('revoked', "Procédure annulée par l'acheteur")],
                             'Statut', readonly=True, index=True, default='new')


    partner_id = fields.Many2one(
        "res.partner",
        string="Pouvoir adjudicateur",
        ondelete="restrict",
        tracking=True,
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
    )

    partner_company_ids = fields.Many2many(
        "res.partner",
        relation="agreement_partner_company_ids",
        string="Donneurs d'ordre",
        tracking=True,
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
    )

    mandator_id = fields.Many2one(
        "res.partner",
        string="Mandataire",
        tracking=True,
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
    )

    cocontractor_ids = fields.Many2many(
        "res.partner",
        relation="agreement_cocontractors_company_ids",
        string="Co-traitants",
        tracking=True,
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
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
        string="Sous-traitants de rang 1",
    )

    active = fields.Boolean(default=True)
    signature_date = fields.Date(tracking=True)
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(string="Date limite de commande", tracking=True)
    end_date_contractors = fields.Date(string="Date de fin d'exécution des prestations", tracking=True)
    passed_time_rate = fields.Float("%age écoulé (durée)", compute=compute)
    end_of_year_discount = fields.Html("Remise de fin d'année", help="Décrire ici les modalités de remise de fin d'année, le cas échéant")

    comments = fields.Html('Commentaires')
    referent = fields.Many2one("res.users", string="Référent Galaxie")
    teams_link = fields.Char("Lien Teams")

    win_announcement = fields.Char("URL vers l'annonce d'attribution", help="Lien vers l'annonce au BODACC de l'attribution du marché")

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        string="Currency",
        readonly=True
    )
    max_amount = fields.Monetary("Montant max de l'accord", store=True)

    is_galaxy_agreement = fields.Boolean("Marché de la galaxie", compute=compute, help="Une entreprise de la galaxie est titulaire ou bien co-traitante de ce marché.")

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

    """
    def name_get(self):
        res = []
        for agr in self:
            name = agr.name
            if agr.code:
                name = "[{}] {}".format(agr.code, agr.name)
            res.append((agr.id, name))
        return res
    """

    _sql_constraints = [
        (
            "code_partner_company_unique",
            "unique(code, partner_id)",
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
