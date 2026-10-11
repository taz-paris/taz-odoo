from odoo import models, fields, api


class ProjectEvaluationAssessor(models.Model):
    _name = 'project.evaluation.assessor'
    _description = "Évaluateur d'une évaluation de mission"
    # Pas d'identité propre : le nom affiché (ex. pour le widget many2many_tags sur
    # project.evaluation.assessor_ids) est celui de l'évaluateur.
    _rec_name = 'employee_id'

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
    display_name = fields.Char(compute='_compute_display_name', search='_search_display_name')

    @api.depends('employee_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.employee_id.display_name or ''

    @api.model
    def _search_display_name(self, operator, value):
        return [('employee_id', operator, value)]


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
