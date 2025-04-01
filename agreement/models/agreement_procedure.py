from odoo import _, api, fields, models
import datetime
import logging
_logger = logging.getLogger(__name__)

class AgreementProcedure(models.Model):
    _name = "agreement.procedure"
    _description = "Agreement procedure"

    name = fields.Char("Nom")
    partner_id = fields.Many2one(
        "res.partner",
        string="Pouvoir adjudicateur",
        ondelete="restrict",
        domain="[('is_company', '=', True), ('type', '=', 'contact')]",
        required=True,
    )
    agreement_ids = fields.One2many('agreement', 'agreement_procedure_id', string="Lots")
    win_announcement = fields.Char("URL vers l'annonce d'attribution", help="Lien vers l'annonce au BODACC de l'attribution du marché")
