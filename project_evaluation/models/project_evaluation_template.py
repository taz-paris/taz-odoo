from odoo import models, fields


class ProjectEvaluationTemplate(models.Model):
    _name = 'project.evaluation.template'
    _description = "Gabarit d'évaluation de mission"

    name = fields.Char("Nom", required=True)
    active = fields.Boolean("Actif", default=True)
    schema = fields.Text(
        "Schéma (JSON)",
        help="Définition JSON-Schema des types de champs du formulaire, au format JSON brut tel que reçu de la source externe. Ne décrit que les types : pas de libellés ni de mise en page (voir le champ form pour ça).",
    )
    form = fields.Text(
        "Formulaire (JSON)",
        help="Arbre de présentation du formulaire (composants, titres, textes d'aide, options...), au format JSON brut tel que reçu de la source externe. C'est cette structure qui permet de rendre lisiblement le contenu d'une évaluation.",
    )
    form_template = fields.Text(
        "Formulaire éditeur (JSON)",
        help="Représentation interne de l'éditeur de formulaire de la source externe (plus riche mais moins directement exploitable que le champ form), au format JSON brut tel que reçu.",
    )
    evaluation_ids = fields.One2many('project.evaluation', 'template_id', string="Évaluations")
    evaluation_count = fields.Integer("Nombre d'évaluations", compute='_compute_evaluation_count')

    def _compute_evaluation_count(self):
        for rec in self:
            rec.evaluation_count = len(rec.evaluation_ids)

    def action_open_evaluations(self):
        self.ensure_one()
        return {
            'name': "Évaluations",
            'type': 'ir.actions.act_window',
            'res_model': 'project.evaluation',
            'view_mode': 'list,form',
            'domain': [('template_id', '=', self.id)],
        }
