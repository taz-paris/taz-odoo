from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployeeSkill(models.Model):
    _inherit = 'hr.employee.skill'

    # Le niveau n'est plus obligatoire (core : required=True) : on doit pouvoir enregistrer une
    # compétence pas encore évaluée (ex. un intérêt déclaré sur Napta sans note associée -- cf.
    # create_update_odoo_interest/create_update_odoo_evaluation dans napta_connector).
    skill_level_id = fields.Many2one(required=False)

    interest = fields.Selection([
        ('yes', 'Oui'),
        ('no', 'Non'),
        ], string="Souhaite développer cette compétence")
    grade_ids = fields.One2many('hr.employee.skill.grade', 'employee_skill_id', string="Notes")

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        # Surcharge de la contrainte core (qui rejette toute valeur vide, y compris False) : on
        # n'exige la cohérence skill_level_id/skill_type_id que lorsqu'un niveau est renseigné.
        for record in self:
            if record.skill_level_id and record.skill_level_id not in record.skill_type_id.skill_level_ids:
                raise ValidationError(_(
                    "The skill level %(level)s is not valid for skill type: %(type)s",
                    level=record.skill_level_id.name, type=record.skill_type_id.name))

    @api.depends('skill_id', 'skill_level_id')
    def _compute_display_name(self):
        for employee_skill in self:
            if employee_skill.skill_level_id:
                employee_skill.display_name = f"{employee_skill.skill_id.name}: {employee_skill.skill_level_id.name}"
            else:
                employee_skill.display_name = employee_skill.skill_id.name or ''

    skill_is_certification = fields.Boolean(related='skill_id.is_certification')
    obtained_date = fields.Date("Date d'obtention")
    expiry_date = fields.Date("Date d'expiration", compute='_compute_expiry_date', store=True)

    @api.depends('obtained_date', 'skill_id.is_certification', 'skill_id.validity_duration_in_months')
    def _compute_expiry_date(self):
        for rec in self:
            if not rec.skill_id.is_certification or not rec.obtained_date:
                rec.expiry_date = False
            else:
                rec.expiry_date = rec.obtained_date + relativedelta(months=rec.skill_id.validity_duration_in_months)

    def _recompute_skill_level_from_grades(self):
        # Reproduit la règle Napta (cf. doc "Calcul des scores de compétences et affichage") :
        # - s'il existe au moins une note tierce (pas d'auto-évaluation), le niveau courant est celui
        #   de la note tierce la plus récente (Napta propose aussi la moyenne selon la config de
        #   l'organisation ; on a choisi "la plus récente" ici) -- l'auto-évaluation est alors exclue.
        # - sinon, le niveau courant est celui de l'auto-évaluation la plus récente (il ne devrait y en
        #   avoir qu'une : Napta ne garde pas d'historique des auto-évaluations, une nouvelle écrase
        #   l'ancienne -- mais on prend la plus récente par sécurité si plusieurs existaient quand même).
        # - sinon (aucune note du tout), le niveau est vidé.
        #
        # Appelé automatiquement par hr.employee.skill.grade (create/write/unlink), sauf dans le
        # contexte skip_skill_level_recompute=True (utilisé par napta_connector : tant que Napta reste
        # la source, c'est lui qui fournit le niveau courant déjà calculé, potentiellement à partir de
        # notes qu'on ne voit pas nous-mêmes -- cf. notes hors évaluation de mission, non synchronisables).
        for rec in self:
            peer_grades = rec.grade_ids.filtered(lambda g: not g.is_self_assessment and g.skill_level_id)
            if peer_grades:
                new_level = peer_grades.sorted(key=lambda g: g.graded_on or g.create_date, reverse=True)[0].skill_level_id
            else:
                self_grades = rec.grade_ids.filtered(lambda g: g.is_self_assessment and g.skill_level_id)
                new_level = self_grades.sorted(key=lambda g: g.graded_on or g.create_date, reverse=True)[0].skill_level_id if self_grades else False
            if rec.skill_level_id != new_level:
                rec.skill_level_id = new_level
