# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import datetime 

import logging
_logger = logging.getLogger(__name__)


class tazResIndustry(models.Model):
    #_inherit = ['res.partner.industry', 'mail.thread']
    _inherit = 'res.partner.industry'

    ms_planner_plan_id = fields.Char("M$ planner plan ID", help="Id of the Microsoft Planner plan where tasks should be created for business action of that industry")
    pillar_id = fields.Many2one('res.partner.industry.pillar', string = "Pillier")
    user_id = fields.Many2one('res.users', string='Responsable du compte')#, tracking=True)
    challenger_id = fields.Many2one('res.users', string='Compte challenger')#, tracking=True)
    contributor_ids = fields.Many2many('res.users', string='Contributeurs')#, tracking=True)
    partner_ids = fields.One2many('res.partner', 'industry_id', string="Entreprises", domain=[('active', '=', True), ('is_company', '=', True), ('type', '=', 'contact')])
    account_plan_url = fields.Char("Lien vers le dossier du plan de compte")
    business_priority = fields.Selection([
         ('active', '1-Compte actif'),
         ('priority_target', '2-Compte prioritaire'),
         ('not_tracked', '3-Opportunités'),
         ('inditto', '4-Contribution Inditto'),
    ], "Niveau de priorité", default='not_tracked')#, tracking=True)

    customer_book_goal_ids = fields.One2many('taz.customer_book_goal', 'industry_id')  
    customer_book_followup_ids = fields.One2many('taz.customer_book_followup', 'industry_id')  
    business_partner_company_ids = fields.Many2many('res.partner', domain=[('ref_company_ids', '!=', False)], string="Galaxie")


    def get_book_by_period(self, begin_date, end_date, company_id):
        #TODO si 1/1/2024 00:00:00 => le projet n'est pas compté sur 2024
        #   > problème de conversion à la date GMT ?
        #   ATTENTION : ça ne sort pas non plus sur le TCD => bug coeur Odoo ?
        search_param_list = [
            ('stage_is_part_of_booking', '=', True), 
            ('partner_id', 'in', self.partner_ids.ids),
            ('date_win_loose', '>=', begin_date),
            ('date_win_loose', '<=', end_date),
            ('reporting_sum_company_outsource_code3_code_4', '!=', False),
            ('company_id', '=', company_id.id),
        ]
        project_ids = self.env['project.project'].sudo().search(search_param_list)
        book_period = 0.0
        for project in project_ids:
            book_period += project.reporting_sum_company_outsource_code3_code_4
        return book_period, project_ids

    def get_book_delta(self, begin_date, end_date, company_id):
        # This function returns the projects with date_win_loose in the period (usually current year) and customer_book changed within the last 31 days
        search_param_list = [
            ('stage_is_part_of_booking', '=', True),
            ('date_win_loose', '>=', begin_date),
            ('date_win_loose', '<=', end_date),
            ('partner_id', 'in', self.partner_ids.ids),
            ('company_id', '=', company_id.id),
        ]
        project_ids = self.env['project.project'].sudo().search(search_param_list)
        book_period = 0.0
        target_project_ids = []
        for project in project_ids:
            if project.reporting_sum_company_outsource_code3_code_4_delta != 0:
                book_period += project.reporting_sum_company_outsource_code3_code_4_delta
                target_project_ids.append(project.id)
        return book_period, target_project_ids

    def get_number_of_opportunities(self, company_id):
        search_param_list = [
            ('partner_id', 'in', self.partner_ids.ids),
            ('stage_is_part_of_booking', '=', False),
            ('state', '=', 'before_launch'),
            ('company_id', '=', company_id.id),
        ]
        project_ids = self.env['project.project'].sudo().search(search_param_list)
        return len(project_ids), project_ids

    def action_open_account_plan_url(self):
        if self.account_plan_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.account_plan_url,
                'target': 'new',
            }
        else :
            raise ValidationError(_("Ce projet n'est lié à aucun plan de compte : impossible de l'ouvrir."))


    def action_open_contacts(self):
        contact_ids = []
        for partner_id in self.partner_ids:
            contact_ids += partner_id.child_ids_contact.ids

        action = {
            'name': _('Liste des contacts des entreprises du compte '+self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'view_id': [self.env.ref("taz-common.contact_tree").id, self.env.ref("taz-common.contact_form").id],
            'domain': [('id', 'in', contact_ids)],
            'target': 'current',
            'limit': 150,
            'groups_limit': 150,
            'context': {
            }
        }

        return action

    def action_open_business_actions(self):
        business_action_ids = self.env['taz.business_action'].search([('parent_partner_industry_id', '=', self.id)])

        action = {
            'name': _('Liste des actions commerciales des entreprises du compte '+self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'taz.business_action',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', business_action_ids.ids)],
            'target': 'current',
            'limit': 150,
            'groups_limit': 150,
            'context': {
                'search_default_state_not_done_not_cancelled': 1
            }
        }

        return action
