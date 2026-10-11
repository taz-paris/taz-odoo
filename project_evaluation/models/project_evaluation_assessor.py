from odoo import models, fields, api


class ProjectEvaluationAssessor(models.Model):
    _name = 'project.evaluation.assessor'
    _description = "Évaluateur d'une évaluation de mission"

    evaluation_id = fields.Many2one(
        'project.evaluation',
        string="Évaluation",
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one('hr.employee', string="Évaluateur", required=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Fait'),
        ], string="Statut", default='pending', required=True)
    validated_on = fields.Datetime("Date de validation", readonly=True)

    _sql_constraints = [
        ('evaluation_employee_uniq', 'UNIQUE (evaluation_id, employee_id)',
         "Cet évaluateur est déjà associé à cette évaluation."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state') == 'done' and 'validated_on' not in vals:
                vals['validated_on'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals and 'validated_on' not in vals:
            vals['validated_on'] = fields.Datetime.now() if vals['state'] == 'done' else False
        return super().write(vals)
