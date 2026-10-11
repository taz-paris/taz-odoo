from odoo import models, fields


class HrEmployeeSkillGrade(models.Model):
    _inherit = 'hr.employee.skill.grade'

    project_evaluation_id = fields.Many2one(
        'project.evaluation',
        string="Évaluation de mission",
        ondelete='set null',
        help="Facultatif : une note de compétence n'est pas forcément liée à une évaluation de mission.",
    )

    _sql_constraints = [
        ('project_evaluation_skill_rater_uniq',
         'UNIQUE (project_evaluation_id, skill_id, rater_employee_id)',
         "Cette compétence a déjà été notée par cette personne sur cette évaluation."),
    ]
