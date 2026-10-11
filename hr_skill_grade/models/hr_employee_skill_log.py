from odoo import models, fields


class HrEmployeeSkillLog(models.Model):
    _inherit = 'hr.employee.skill.log'

    # Même raison que sur hr.employee.skill.skill_level_id : hr.employee.skill._create_logs() écrit
    # ici le niveau courant de CHAQUE compétence de l'employé (pas seulement celle modifiée) à chaque
    # create/write -- si une seule de ces compétences n'a pas de niveau, ça doit rester possible.
    skill_level_id = fields.Many2one(required=False)
