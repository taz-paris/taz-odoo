from odoo import models, fields


class ProjectEvaluationTemplate(models.Model):
    _name = 'project.evaluation.template'
    _description = "Gabarit d'évaluation de mission"

    name = fields.Char("Nom", required=True)
    active = fields.Boolean("Actif", default=True)
    schema = fields.Text(
        "Schéma (JSON)",
        help="Définition du formulaire d'évaluation (questions/critères), au format JSON brut tel que reçu de la source externe.",
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
