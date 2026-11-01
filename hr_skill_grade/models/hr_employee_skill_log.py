from odoo import models, fields


class HrEmployeeSkillLog(models.Model):
    """Journal d'état natif (snapshot quotidien du niveau courant), rempli automatiquement par
    hr.employee.skill._create_logs() -- voir hr.employee.skill.grade pour le journal des
    notations (auteur, commentaire, auto vs tierce évaluation) qui pilote ce niveau courant.
    Ce modèle n'est pas lu ni modifié ailleurs dans hr_skill_grade en dehors de ce fichier.
    """
    _inherit = 'hr.employee.skill.log'

    # Même raison que sur hr.employee.skill.skill_level_id : hr.employee.skill._create_logs() écrit
    # ici le niveau courant de CHAQUE compétence de l'employé (pas seulement celle modifiée) à chaque
    # create/write -- si une seule de ces compétences n'a pas de niveau, ça doit rester possible.
    skill_level_id = fields.Many2one(required=False)
