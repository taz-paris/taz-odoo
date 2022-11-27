# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class tazResIndustry(models.Model):
    _inherit = "res.partner.industry"

    ms_planner_plan_id = fields.Char("M$ planner plan ID", help="Id of the Microsoft Planner plan where tasks should be created for business action of that industry")
    pillar_id = fields.Many2one('res.partner.industry.pillar', string = "Pillier")
    user_id = fields.Many2one('res.users', string='Business Domaine Leader')
    partner_ids = fields.One2many('res.partner', 'industry_id', string="Entreprises")
