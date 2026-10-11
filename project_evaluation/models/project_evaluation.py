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
    assessor_ids = fields.One2many('project.evaluation.assessor', 'evaluation_id', string="Évaluateurs")
    employee_validated = fields.Boolean("Validée par le consultant", default=False)
    employee_validated_on = fields.Datetime("Date de validation (consultant)", readonly=True)

    def write(self, vals):
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
