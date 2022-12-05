from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import re

from odoo.addons import base

class staffingProject(models.Model):
    _inherit = "project.project"

    def create(self, vals):
        if vals.get('number', 'New') == 'New':
                vals['number'] = self.env['ir.sequence'].next_by_code('project.project') or 'New' 
        res = super().write(vals)
        return res

    staffing_need_ids = fields.One2many('staffing.need', 'project_id')
    order_amount = fields.Float('Montant commande')
    margin_target = fields.Float('Objectif de marge (%)') #TODO : contrôler que c'est positif et <= 100
    number = field.Char('Numéro', readonly=True, required=True, copy=False, default='New')
    is_purchase_order_received = fields.Boolean('Bon de commande reçu')
    outsourcing = fields.Selection([
            ('no-outsourcing', 'Sans sous-traitance'),
            ('co-sourcing', 'Avec Co-traitance'),
            ('direct-paiement-outsourcing', 'Sous-traitance paiement direct'),
            ('direct-paiement-outsourcing-company', 'Sous-traitance paiement direct + Tasmane'),
            ('outsourcing', 'Sous-traitance paiement Tasmane'),
        ], string="Type de sous-traitance")
    #TODO : ajouter un type (notamment pour les accords cadre) ? ou bien utiliser les tags ?
    #TODO : ajouter les personnes intéressées pour bosser sur le projet
    #TODO : ajouter les personnes qui ont travaillé sur la propale
