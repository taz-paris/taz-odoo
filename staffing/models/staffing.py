# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class staffingNeed(models.Model):
    _name = "staffing.need"
    _description = "Record the staffing need"
           
    #TODO : interdire de pointer hors de la période d'affectation

    @api.depends('project_id')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.project_id.name or "", record.job_id.name or "")

    name = fields.Char("Nom", compute=_compute_name)

    project_id = fields.Many2one('project.project', ondelete="restrict", required=True)
    job_id = fields.Many2one('hr.job') #TODO : impossible de le metrte en required car la synchro fitnet importe des assignments qui n'ont pas de job_i
    skill_id = fields.Many2one('hr.skill') #TODO : si on veut pouvoir spécifier le niveau, il faut un autre objet technique qui porte le skill et le level
    considered_employee_ids = fields.Many2many('hr.employee')
    #Pour le moment le, un staffing.need ne porte qu'un seul employé. Si besion de plusieurs employés avec le même profil, il faudra créer plusieurs besoins
    staffed_employee_id = fields.Many2one('hr.employee', string='Personne satffée')
    begin_date = fields.Date('Date début', required=True) #TODO : mettre par defaut la date de début du projet
    end_date = fields.Date('Date fin', required=True) #TODO : mettre par defaut la date de fin du projet
    nb_days_needed = fields.Float('Nb de jours') #TODO : mettre par défaut un temps plein entre les 2 dates si vide
    ##TODO : impossible de le metrte en required car la synchro fitnet importe des assignments qui ont un budget jour initial à 0
    #percent_needed = fields.Float('Pourcentage besoin')

    state = fields.Selection([
        ('open', 'Ouvert'),
        ('done', 'Staffé'),
        ('cancelled', 'Annulé'),
        ('wait', 'En attente')], 'Statut', default='open')

    staffing_proposal_ids = fields.One2many('staffing.proposal', 'staffing_need_id')

    def open_record(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = self.id
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref("staffing.need_form")

        # then open the form
        return {
                'type': 'ir.actions.act_window',
                'name': 'Besoins de staffing',
                'res_model': 'staffing.need',
                'res_id': rec_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': form_id.id,
                'context': {},
                # if you want to open the form in edit mode direclty
                'flags': {'initial_mode': 'edit'},
                'target': 'new',
            }

    @api.model
    def create(self, vals):
        needs = super().create(vals)
        for need in needs:
            if need.status == 'open':
                need.generate_staffing_proposal()
        return needs

    def generate_staffing_proposal(self):
        employees = self.env['hr.employee'].search([])
        for employee in employees:
            employee_job = employee._get_job_id(self.begin_date)
            if not employee_job:
                continue
            if employee_job.id != self.job_id.id: #TODO : remplacer cette ligne par une conditin de recherche lorsque la job_id aura été transformé en fonction
                continue
            _logger.info("generate_staffing_proposal %s" % employee.name)
            needs = self.env['staffing.proposal'].search([('staffing_need_id', '=', self.id),('employee_id', '=', employee.id)])
            if len(needs) == 0:
                dic = {}
                dic['employee_id'] = employee.id
                dic['staffing_need_id'] = self.id
                self.env['staffing.proposal'].create(dic)
                break
        #TODO supprimer les propositions qui ne sont pas sur ces employés (cas de changement de grade de la demande)

    #TODO : lorsqu'une affectation est validée, créer les prévisionnels


class staffingProposal(models.Model):
    _name = "staffing.proposal"
    _description = "Computed staffing proposal"
    _order = "ranked_proposal desc"

    _sql_constraints = [
        ('need_employee_uniq', 'UNIQUE (staffing_need_id, employee_id)',  "Impossible d'enregistrer deux propositions de staffing pour le même besoin et le même consultant.")
    ]

    #@api.depends('staffing_need_id', 'staffing_need_id.begin_date', 'staffing_need_id.end_date', 'employee_id')
    @api.depends('staffing_need_id', 'staffing_need_id.begin_date', 'staffing_need_id.end_date', 'employee_id')
    def compute(self):
        _logger.info('staffingProposal compute %s' % self.employee_id.name)
        #TODO : relancer cette fonction si les timesheet évoluent sur cette période
        need = self.staffing_need_id
        self.employee_availability = self.employee_id.number_days_available_period(need.begin_date, need.end_date)
        self.ranked_employee_availability = self.employee_availability / need.nb_days_needed
        self.ranked_proposal = self.ranked_employee_availability


    @api.depends('staffing_need_id', 'employee_id')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.staffing_need_id.name or "", record.employee_id.name or "")

    name = fields.Char("Nom", compute=_compute_name)
    is_chosen = fields.Boolean('Choisie')
    #Ajouter un lien vers les autres staffing proposal en concurrence (même personne, même période avec une quotité totale de temps > 100%)
    staffing_need_id = fields.Many2one('staffing.need', ondelete="cascade")
    employee_id = fields.Many2one('hr.employee')

    employee_job_id = fields.Many2one(string="Grade", related='employee_id.job_id') #TODO : remplacer le hr.employee.job_id par une fonction qui retourne get_job_id()
    employee_skill_ids = fields.One2many(string="Compétences", related='employee_id.employee_skill_ids')
    employee_last_evaluation = fields.Html(string="Souhaits de staffing COD", related='employee_id.staffing_wishes')
    employee_availability = fields.Float("Dispo sur la période", compute='compute', store=True)

    ranked_proposal = fields.Float('Note globale', compute='compute', store=True)
    ranked_employee_availability = fields.Float('Note disponibilité', compute='compute', store=True)
    ranked_employee_skill = fields.Float('Note adéquation compétences', compute='compute', store=True)
    ranked_employee_explicit_voluntary = fields.Float('A explicitement demandé à être sur cette misison', compute='compute', store=True)
    ranked_employee_worked_on_proposal = fields.Float('A travaillé sur la proposition commerciale', compute='compute', store=True)
    ranked_employee_wished_on_need = fields.Float('Envisagé dans la desciption du besoin', compute='compute', store=True)

