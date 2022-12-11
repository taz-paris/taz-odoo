from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class staffingProject(models.Model):
    _inherit = "project.project"

    #@api.model
    #def create(self, vals):
    #    if vals.get('number', '') == '':
    #            vals['number'] = self.env['ir.sequence'].next_by_code('project.project') or ''
    #    res = super().create(vals)
    #    return res

    def name_get(self):
        res = []
        for rec in self:
            display_name = "%s %s (%s)" % (rec.number or "", rec.name or "", rec.partner_id.name or "")
            res.append((rec.id, display_name))
        return res

    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
    partner_id = fields.Many2one(domain="[('is_company', '=', True)]")
    project_director_employee_id = fields.Many2one('hr.employee', "Directeur de mission", default=lambda self: self.env.user.employee_id) #TODO : synchroniser cette valeur avec user_id avec un oneChange
    staffing_need_ids = fields.One2many('staffing.need', 'project_id')
    probability = fields.Selection([
            ('0', '0 %'),
            ('30', '30 %'),
            ('70', '70 %'),
            ('100', '100 %'),
        ], string='Probabilité')
    order_amount = fields.Float('Montant commande')
    billed_amount = fields.Float('Montant facturé', readonly=True)
    payed_amount = fields.Float('Montant payé', readonly=True)
    margin_target = fields.Float('Objectif de marge (%)') #TODO : contrôler que c'est positif et <= 100
    number = fields.Char('Numéro', readonly=True, required=True, copy=False, default='New')
    is_purchase_order_received = fields.Boolean('Bon de commande reçu')
    purchase_order_number = fields.Char('Numéro du bon de commande')
    remark = fields.Text("Remarques")
    outsourcing = fields.Selection([
            ('no-outsourcing', 'Sans sous-traitance'),
            ('co-sourcing', 'Avec Co-traitance'),
            ('direct-paiement-outsourcing', 'Sous-traitance paiement direct'),
            ('direct-paiement-outsourcing-company', 'Sous-traitance paiement direct + Tasmane'),
            ('outsourcing', 'Sous-traitance paiement Tasmane'),
        ], string="Type de sous-traitance")
    #TODO : ajouter un type (notamment pour les accords cadre) ? ou bien utiliser les tags ?
    #TODO : ajouter les personnes intéressées pour bosser sur le projet
    #TODO : ajouter les personnes qui ont travaillé sur la propale + double book
    #TODO : ajouter un sur-objet "group project"
