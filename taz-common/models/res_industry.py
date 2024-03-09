# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import datetime 

import logging
_logger = logging.getLogger(__name__)


class tazResIndustry(models.Model):
    _inherit = "res.partner.industry"

    ms_planner_plan_id = fields.Char("M$ planner plan ID", help="Id of the Microsoft Planner plan where tasks should be created for business action of that industry")
    pillar_id = fields.Many2one('res.partner.industry.pillar', string = "Pillier")
    user_id = fields.Many2one('res.users', string='Responsable du compte')
    coordinator_id = fields.Many2one('res.users', string='Coordinateur')
    partner_ids = fields.One2many('res.partner', 'industry_id', string="Entreprises", domain=[('active', '=', True), ('is_company', '=', True), ('type', '=', 'contact')])
    account_plan_url = fields.Char("URL vers le PPTX du plan de compte")
    business_priority = fields.Selection([
         ('priority_target', '1-Compte prioritaire'),
         ('active', '2-Compte actif'),
         ('not_tracked', '3-Ni prioritaire, ni actif'),
    ], "Niveau de priorité", default='not_tracked')

    customer_book_goal_ids = fields.One2many('taz.customer_book_goal', 'industry_id')  
    customer_book_followup_ids = fields.One2many('taz.customer_book_followup', 'industry_id')  


    def get_book_by_period(self, begin_date, end_date):
        project_ids = self.env['project.project'].search([
            ('stage_is_part_of_booking', '=', True), 
            ('partner_id', 'in', self.partner_ids.ids),
            ('date_win_loose', '>=', begin_date),
            ('date_win_loose', '<=', end_date),
            ('reporting_sum_company_outsource_code3_code_4', '!=', False),
        ])
        res = 0.0
        for project in project_ids:
            res += project.reporting_sum_company_outsource_code3_code_4
        return res

    def get_number_of_opportunities(self):
        project_count = self.env['project.project'].search_count([
            ('partner_id', 'in', self.partner_ids.ids),
            ('stage_is_part_of_booking', '=', False),
            ('state', '=', 'before_launch'),
        ])
        return project_count
