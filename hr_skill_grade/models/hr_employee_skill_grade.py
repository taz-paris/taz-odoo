from odoo import models, fields, api


class HrEmployeeSkillGrade(models.Model):
    _name = 'hr.employee.skill.grade'
    _description = "Note sur une compétence d'un employé"
    _order = 'id desc'

    employee_skill_id = fields.Many2one('hr.employee.skill', required=True, ondelete='cascade')
    # Champs related pratiques : évitent d'avoir à traverser employee_skill_id.skill_id depuis les
    # vues/widgets (listes, regroupements, lecture côté JS du widget d'évaluation).
    employee_id = fields.Many2one(related='employee_skill_id.employee_id', store=True)
    skill_id = fields.Many2one(related='employee_skill_id.skill_id', store=True)
    skill_type_id = fields.Many2one(related='employee_skill_id.skill_id.skill_type_id', store=True)
    skill_description = fields.Text(related='skill_id.description', string="Description de la compétence")
    rater_employee_id = fields.Many2one('hr.employee', string="Noté par", required=True)
    skill_level_id = fields.Many2one('hr.skill.level', string="Niveau")
    skill_level_description = fields.Text(related='skill_level_id.description', string="Description du niveau")
    comment = fields.Text()
    is_self_assessment = fields.Boolean("Auto-évaluation", compute='_compute_is_self_assessment', store=True)
    graded_on = fields.Datetime(
        "Date de la note",
        help="Date à laquelle la note a été donnée. Alimentée par la source externe quand elle le précise "
             "(ex. Napta), sinon par défaut la date d'enregistrement dans Odoo. Sert à déterminer la note "
             "tierce la plus récente lors du recalcul du niveau courant (hr.employee.skill.skill_level_id).",
        default=fields.Datetime.now,
    )

    @api.depends('rater_employee_id', 'employee_skill_id.employee_id')
    def _compute_is_self_assessment(self):
        for rec in self:
            rec.is_self_assessment = bool(
                rec.rater_employee_id and rec.rater_employee_id == rec.employee_skill_id.employee_id
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_skill_level_recompute'):
            records.employee_skill_id._recompute_skill_level_from_grades()
        return records

    def write(self, vals):
        employee_skills_before = self.employee_skill_id
        res = super().write(vals)
        if not self.env.context.get('skip_skill_level_recompute'):
            (employee_skills_before | self.employee_skill_id)._recompute_skill_level_from_grades()
        return res

    def unlink(self):
        employee_skills = self.employee_skill_id
        res = super().unlink()
        if not self.env.context.get('skip_skill_level_recompute'):
            employee_skills._recompute_skill_level_from_grades()
        return res
