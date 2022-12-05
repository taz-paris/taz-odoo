# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class staffingNeed(models.Model):
    _name = "staffing.need"
    _description = "Record the staffing need"
    #_order = "date_deadline desc"
    #_sql_constraints = [
    #    ('date_partner_uniq', 'UNIQUE (partner_id, date_deadline)',  "Impossible d'enregistrer deux actions commerciales le même jour pour le même client.")
    #]

           
    @api.depends('project_id')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.project_id.name or "", record.job_id.name or "")

    name = fields.Char("Nom", compute=_compute_name)

    project_id = fields.Many2one('project.project')
    job_id = fields.Many2one('hr.job')
    skill_id = fields.Many2one('hr.skill') #TODO : si on veut pouvoir spécifier le niveau, il faut un autre objet technique qui porte le skill et le level
    considered_employee_ids = fields.Many2many('hr.employee')
    #Pour le moment le, un staffing.need ne porte qu'un seul employé. Si besion de plusieurs employés avec le même profil, il faudra créer plusieurs besoins
    staffed_employee_id = fields.Many2one('hr.employee', string='Personne satffée')
    begin_date = fields.Date('Date début')
    end_date = fields.Date('Date fin')
    percent_needed = fields.Float('Pourcentage besoin')

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
                'target': 'current',
            }

class staffingProposal(models.Model):
    _name = "staffing.proposal"
    _description = "Computed staffing proposal"
    _order = "ranked_proposal desc"


    @api.depends('staffing_need_id', 'employee_id')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.staffing_need_id.name or "", record.employee_id.name or "")

    name = fields.Char("Nom", compute=_compute_name)
    is_chosen = fields.Boolean('Choisie')
    #Ajouter un lien vers les autres staffing proposal en concurrence (même personne, même période avec une quotité totale de temps > 100%)
    staffing_need_id = fields.Many2one('satffing.need')
    employee_id = fields.Many2one('hr.employee')

    employee_job_id = fields.Many2one(related='employee_id.job_id')
    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
    #employee_last_evaluation =
    #employee_availability = 

    ranked_proposal = fields.Float('Note globale')
    ranked_employee_availability = fields.Float('Note disponibilité')
    ranked_employee_skill = fields.Float('Note adéquation compétences')
    ranked_employee_explicit_voluntary = fields.Float('A explicitement demandé à être sur cette misison')
    ranked_employee_worked_on_proposal = fields.Float('A travaillé sur la proposition commerciale')
    ranked_employee_wished_on_need = fields.Float('Envisagé dans la desciption du besoin')

