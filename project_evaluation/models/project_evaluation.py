import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectEvaluation(models.Model):
    _name = 'project.evaluation'
    _description = "Évaluation de mission"
    _order = 'id desc'
    _check_company_auto = True

    @api.depends('project_id', 'employee_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s - %s" % (rec.project_id.name or "", rec.employee_id.name or "")

    name = fields.Char("Nom", compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Consultant",
        required=True,
        check_company=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string="Projet",
        required=True,
        check_company=True,
    )
    partner_id = fields.Many2one(related='project_id.partner_id', string="Client", store=True)
    template_id = fields.Many2one('project.evaluation.template', string="Gabarit")
    template_form_template = fields.Text(
        related='template_id.form_template',
        string="Formulaire éditeur du gabarit (technique)",
    )
    data = fields.Text(
        "Contenu (JSON)",
        help="Réponses de l'évaluation, au format JSON brut tel que reçu de la source externe.",
    )
    state = fields.Selection([
        ('ongoing', 'En cours'),
        ('closed', 'Fermée'),
        ], string="Statut", default='ongoing', required=True,
        help="Une évaluation passe à Fermée quand elle a été approuvée par l'évalué ET par au moins un évaluateur.")
    is_published = fields.Boolean(
        "Publiée",
        default=True,
        help="Si décochée, l'évaluation est en mode brouillon évaluateur : son contenu reste invisible pour l'évalué, indépendamment du statut En cours/Fermée.",
    )
    assessor_ids = fields.One2many(
        'project.evaluation.assessor',
        'evaluation_id',
        string="Évaluateurs",
    )
    skill_grade_ids = fields.One2many('hr.employee.skill.grade', 'project_evaluation_id', string="Notes de compétences")
    employee_validated = fields.Boolean("Validée par le consultant", default=False)
    employee_validated_on = fields.Datetime("Date de validation (consultant)", readonly=True)
    can_validate = fields.Boolean(
        "Peut valider",
        compute='_compute_can_validate',
        help="Technique : vrai si l'utilisateur courant est le consultant évalué, pour piloter l'accès en "
             "écriture à employee_validated dans la vue.",
    )

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_can_validate(self):
        for rec in self:
            rec.can_validate = bool(rec.employee_id.user_id and rec.employee_id.user_id == self.env.user)

    can_approve = fields.Boolean(
        "Peut approuver",
        compute='_compute_can_approve',
        help="Technique : pilote la visibilité du bouton Approuver. Vrai si l'utilisateur courant est "
             "l'évalué et n'a pas encore validé, ou un évaluateur qui n'a pas encore validé sa propre ligne.",
    )

    @api.depends_context('uid')
    @api.depends('state', 'employee_id', 'employee_validated', 'assessor_ids.employee_id', 'assessor_ids.state')
    def _compute_can_approve(self):
        for rec in self:
            if rec.state == 'closed':
                rec.can_approve = False
                continue
            if rec.employee_id.user_id and rec.employee_id.user_id == self.env.user:
                rec.can_approve = not rec.employee_validated
                continue
            my_assessors = rec.assessor_ids.filtered(lambda a: a.employee_id.user_id == self.env.user)
            rec.can_approve = any(a.state == 'pending' for a in my_assessors)

    can_edit_content = fields.Boolean(
        "Peut modifier le contenu",
        compute='_compute_can_edit_content',
        help="Technique : vrai si l'utilisateur courant est l'évalué ou un évaluateur de cette évaluation "
             "(quel que soit leur propre statut de validation) -- pilote l'accès en écriture au contenu "
             "(data, notes de compétences) dans la vue. Un project.group_project_manager qui n'est ni l'un "
             "ni l'autre reste en lecture seule sur ce contenu, bien qu'il garde l'accès admin au reste "
             "de l'évaluation.",
    )

    @api.depends_context('uid')
    @api.depends('employee_id', 'assessor_ids.employee_id')
    def _compute_can_edit_content(self):
        for rec in self:
            is_evaluee = bool(rec.employee_id.user_id and rec.employee_id.user_id == self.env.user)
            is_assessor = bool(rec.assessor_ids.filtered(lambda a: a.employee_id.user_id == self.env.user))
            rec.can_edit_content = is_evaluee or is_assessor

    other_evaluation_ids = fields.Many2many(
        'project.evaluation',
        compute='_compute_other_evaluation_ids',
        string="Autres évaluations",
        help="Technique : les autres évaluations de ce consultant sur ce projet, pour l'onglet "
             "'Autres évaluations'.",
    )

    @api.depends('project_id', 'employee_id')
    def _compute_other_evaluation_ids(self):
        for rec in self:
            if rec.project_id and rec.employee_id:
                rec.other_evaluation_ids = self.search([
                        ('project_id', '=', rec.project_id.id),
                        ('employee_id', '=', rec.employee_id.id),
                        ('id', '!=', rec.id),
                    ])
            else:
                rec.other_evaluation_ids = False

    def action_approve(self):
        self.ensure_one()
        if self.employee_id.user_id and self.employee_id.user_id == self.env.user:
            self.write({'employee_validated': True, 'employee_validated_on': fields.Datetime.now()})
            return
        my_assessors = self.assessor_ids.filtered(lambda a: a.employee_id.user_id == self.env.user)
        if my_assessors:
            my_assessors.write({'state': 'done'})
            return
        raise UserError(_("Vous n'êtes ni l'évalué, ni un évaluateur de cette évaluation."))

    def add_skill_grade(self, skill_id, skill_level_id=False, comment=False):
        # Permet à l'évalué ou à un évaluateur d'ajouter, depuis le widget d'aperçu, une note de
        # compétence propre à Odoo (pas de remontée vers Napta : l'API ne le permet pas -- cf.
        # EvaluationPreview côté JS). Ne fait plus de sudo() : les ACL/ir.rule natives + celles de
        # hr_skill_grade suffisent maintenant (hr.group_hr_user donné à tous les managers/évaluateurs
        # -> accès complet ; hr_employee_skill_grade_rule_own -> chacun peut créer ses propres notes,
        # y compris en auto-évaluation). Cette méthode reste nécessaire pour deux raisons métier que
        # l'ACL seule ne couvre pas : bloquer l'ajout sur une évaluation clôturée, et créer au passage
        # le hr.employee.skill sous-jacent s'il n'existe pas encore.
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_("Impossible d'ajouter une note de compétence sur une évaluation clôturée."))
        rater_employee = self.env.user.employee_id
        if not rater_employee or not self.can_edit_content:
            raise UserError(_("Seuls l'évalué et les évaluateurs de cette évaluation peuvent ajouter une note de compétence."))

        skill = self.env['hr.skill'].browse(skill_id)
        if not skill.exists():
            raise UserError(_("Compétence introuvable."))

        employee_skill = self.env['hr.employee.skill'].search([
                ('employee_id', '=', self.employee_id.id), ('skill_id', '=', skill.id),
            ])
        if not employee_skill:
            employee_skill = self.env['hr.employee.skill'].create({
                    'employee_id': self.employee_id.id,
                    'skill_id': skill.id,
                    'skill_type_id': skill.skill_type_id.id,
                })

        # Upsert : un même auteur ne peut avoir qu'UNE note par compétence sur une même évaluation
        # (cf. contrainte SQL project_evaluation_skill_rater_uniq). On met à jour sa note existante
        # plutôt que d'en créer une 2e en double, quel que soit le chemin emprunté côté widget
        # ("Ajouter ma note" sur une compétence déjà notée, ou "Ajouter une compétence" en
        # sélectionnant une compétence qu'il a déjà notée via la recherche).
        existing_grade = self.env['hr.employee.skill.grade'].search([
                ('employee_skill_id', '=', employee_skill.id),
                ('project_evaluation_id', '=', self.id),
                ('rater_employee_id', '=', rater_employee.id),
            ])
        grade_vals = {
                'employee_skill_id': employee_skill.id,
                'rater_employee_id': rater_employee.id,
                'skill_level_id': skill_level_id or False,
                'comment': comment or False,
                'project_evaluation_id': self.id,
            }
        if existing_grade:
            existing_grade.write(grade_vals)
        else:
            self.env['hr.employee.skill.grade'].create(grade_vals)

    def delete_skill_grade(self, grade_id):
        # Seul l'auteur d'une note peut la supprimer, et seulement tant que l'évaluation n'est pas
        # clôturée -- même esprit que add_skill_grade. L'ACL/ir.rule (hr_employee_skill_grade_rule_own)
        # autorise déjà l'auteur à supprimer ses propres notes, mais ne sait pas vérifier la clôture
        # de l'évaluation : d'où ce contrôle explicite ici.
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_("Impossible de supprimer une note de compétence sur une évaluation clôturée."))
        grade = self.env['hr.employee.skill.grade'].browse(grade_id)
        if not grade.exists() or grade.project_evaluation_id != self:
            raise UserError(_("Note de compétence introuvable sur cette évaluation."))
        rater_employee = self.env.user.employee_id
        if not rater_employee or grade.rater_employee_id != rater_employee:
            raise UserError(_("Seul l'auteur d'une note peut la supprimer."))
        grade.unlink()

    def _has_data_content(self):
        self.ensure_one()
        if not self.data:
            return False
        try:
            parsed = json.loads(self.data)
        except ValueError:
            return bool(self.data)
        return bool(parsed)

    def write(self, vals):
        if vals.get('employee_validated') and not self.env.context.get('skip_employee_validated_check'):
            # On ne restreint que le passage à True (cocher = revendiquer sa propre validation) :
            # la remise à False (ex. quand le contenu change, cf. plus bas) reste libre, ce n'est pas
            # une usurpation de validation.
            for rec in self:
                if not rec.can_validate:
                    raise UserError(_("Seul le consultant évalué peut valider cette évaluation."))

        if 'template_id' in vals:
            for rec in self:
                if rec.template_id.id != vals['template_id'] and rec._has_data_content():
                    raise UserError(_("Impossible de changer le gabarit d'une évaluation dont le contenu n'est pas vide."))

        if 'data' in vals:
            if self.filtered(lambda rec: rec.state == 'closed'):
                # Sur Napta, une évaluation clôturée ne peut plus être éditée, par personne : même règle ici.
                raise UserError(_("Impossible de modifier le contenu d'une évaluation clôturée."))

            # Toute modification du contenu remet les validations à zéro : chacun doit revalider.
            # (Non documenté côté Napta pour l'instant, mais c'est le comportement sûr à adopter côté Odoo.)
            if 'employee_validated' not in vals:
                vals['employee_validated'] = False
                vals['employee_validated_on'] = False
            res = super().write(vals)
            if 'assessor_ids' not in vals:
                self.mapped('assessor_ids').filtered(lambda a: a.state != 'pending').write({'state': 'pending'})
            return res

        return super().write(vals)
