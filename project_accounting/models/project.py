from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class staffingProject(models.Model):
    _inherit = "project.project"
    _order = "number desc"


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

    def name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|', '|', ('number', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    #inspiré de https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_timesheet/models/hr_timesheet.py#L116
    @api.depends('project_director_employee_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.project_director_employee_id.user_id if rec.project_director_employee_id else False

    def write(self, vals):
        for record in self :
            if 'stage_id' in vals.keys():
                vals['state_last_change_date'] = datetime.today()
        return super().write(vals)

    @api.model
    def create(self, vals):
        vals['state_last_change_date'] = datetime.today()
        return super().create(vals)
 
    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
    stage_is_part_of_booking = fields.Boolean()#related="stage_id.is_part_of_booking")
    partner_id = fields.Many2one(domain="[('is_company', '=', True)]")
    project_group_id = fields.Many2one('project.group', string='Groupe de projets', domain="[('partner_id', '=', partner_id)]")
        #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    project_director_employee_id = fields.Many2one('hr.employee', "Directeur de mission", default=lambda self: self.env.user.employee_id) #TODO : synchroniser cette valeur avec user_id avec un oneChange
    probability = fields.Selection([
            ('0', '0 %'),
            ('30', '30 %'),
            ('70', '70 %'),
            ('100', '100 %'),
        ], string='Probabilité')
    billed_amount = fields.Float('Montant facturé', readonly=True)
    payed_amount = fields.Float('Montant payé', readonly=True)
    state_last_change_date = fields.Date('Date de dernier changement de statut', help="Utilisé pour le filtre Nouveautés de la semaine")

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
    #TODO : ajouter les personnes qui ont travaillé sur la propale + double book


    @api.depends('company_part_amount_initial', 'company_part_cost_initial', 'company_part_amount_current', 'company_part_cost_current', 'outsource_part_amount_initial', 'outsource_part_cost_initial', 'outsource_part_amount_current', 'outsource_part_cost_current', 'other_part_amount_initial', 'other_part_cost_initial', 'other_part_amount_current', 'other_part_cost_current')
    def compute(self):
        for rec in self:
            ######## TOTAL
            rec.order_amount = rec.company_part_amount_initial + rec.outsource_part_amount_initial + rec.other_part_amount_initial

            rec.order_cost_initial = rec.company_part_cost_initial + rec.outsource_part_cost_initial + rec.other_part_cost_initial
            rec.order_marging_amount_initial = rec.company_part_marging_amount_initial + rec.outsource_part_marging_amount_initial + rec.other_part_marging_amount_initial
            rec.order_marging_rate_initial = 0.0
            if rec.order_amount != 0 : 
                rec.order_marging_rate_initial = rec.order_marging_amount_initial / rec.order_amount * 100

            rec.order_cost_current = rec.company_part_cost_current + rec.outsource_part_cost_current + rec.other_part_cost_current
            rec.order_marging_amount_current = rec.company_part_marging_amount_current + rec.outsource_part_marging_amount_current + rec.other_part_marging_amount_current
            rec.order_marging_rate_current = 0.0
            if rec.order_amount != 0 : 
                rec.order_marging_rate_current = rec.order_marging_amount_current / rec.order_amount * 100

            ######## COMPANY PART
            rec.company_part_marging_amount_initial =  rec.company_part_amount_initial - rec.company_part_cost_initial
            rec.company_part_marging_rate_initial = 0.0
            if rec.company_part_amount_initial != 0 :
                rec.company_part_marging_rate_initial = rec.company_part_marging_amount_initial / rec.company_part_amount_initial * 100
    
            rec.company_part_marging_amount_current =  rec.company_part_amount_current - rec.company_part_cost_current
            rec.company_part_marging_rate_current = 0.0
            if rec.company_part_amount_current != 0 :
                rec.company_part_marging_rate_current = rec.company_part_marging_amount_current / rec.company_part_amount_current * 100
    
            ######## OUTSOURCE PART
            rec.outsource_part_marging_amount_initial =  rec.outsource_part_amount_initial - rec.outsource_part_cost_initial
            rec.outsource_part_marging_rate_initial = 0.0 
            if rec.outsource_part_amount_initial != 0 :                
                rec.outsource_part_marging_rate_initial = rec.outsource_part_marging_amount_initial / rec.outsource_part_amount_initial * 100
                                                                
            rec.outsource_part_marging_amount_current =  rec.outsource_part_amount_current - rec.outsource_part_cost_current
            rec.outsource_part_marging_rate_current = 0.0 
            if rec.outsource_part_amount_current != 0 :
                rec.outsource_part_marging_rate_current = rec.outsource_part_marging_amount_current / rec.outsource_part_amount_current * 100

            ######## OTHER PART
            rec.other_part_marging_amount_initial =  rec.other_part_amount_initial - rec.other_part_cost_initial
            rec.other_part_marging_rate_initial = 0.0
            if rec.other_part_amount_initial != 0 :
                rec.other_part_marging_rate_initial = rec.other_part_marging_amount_initial / rec.other_part_amount_initial * 100

            rec.other_part_marging_amount_current =  rec.other_part_amount_current - rec.other_part_cost_current
            rec.other_part_marging_rate_current = 0.0
            if rec.other_part_amount_current != 0 :
                rec.other_part_marging_rate_current = rec.other_part_marging_amount_current / rec.other_part_amount_current * 100



    final_customer_order_amount = fields.Monetary('Montant commandé', help="Montant total commandé par le client final (supérieur au montant piloté par Tasmane si Tasmane est sous-traitant. Egal au montant piloté par Tasmne sinon.)")
    #TODO : ajouter un contrôle : le montant commandé ne peut être inférieur au montant piloté par Tasmane


    ######## TOTAL
    order_amount = fields.Monetary('Montant piloté par Tasmane (fixe ???)', store=True, compute=compute,  help="Montant effectivement commandé à Tasmane : dispositif Tasmane + Sous-traitance (qu'elle soit en paiment direct ou non)")
    #TODO : ajouter un contrôme opur vérifier que self.company_part_amount_initial+self.outsource_part_amount_initial == self.company_part_amount_current+self.outsource_part_amount_current
    order_cost_initial = fields.Monetary('Coût total initial', compute=compute)
    order_marging_amount_initial = fields.Monetary('Marge totale (€) initiale', compute=compute)
    order_marging_rate_initial = fields.Float('Marge totale (%) initiale', compute=compute)

    order_cost_current = fields.Monetary('Coût total actuel', compute=compute)
    order_marging_amount_current = fields.Monetary('Marge totale (€) actuelle', compute=compute)
    order_marging_rate_current = fields.Float('Marge totale (%) actuelle', compute=compute)

    ######## COMPANY PART
    company_part_amount_initial = fields.Monetary('Montant dispositif Tasmane initial', help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_initial = fields.Monetary('Coût de production dispo Tasmane (€) initial', help="Montant du pointage Tasname valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_initial = fields.Monetary('Marge sur dispo Tasmane (€) initiale', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_initial = fields.Float('Marge sur dispo Tasmane (%) initiale', store=True, compute=compute)

    company_part_amount_current = fields.Monetary('Montant dispositif Tasmane actuel', help="Montant produit par le dispositif Tasmane : part produite par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge")
    company_part_cost_current = fields.Monetary('Coût de production dispo Tasmane (€) actuel', help="Montant du pointage Tasname valorisé (pointage par les salariés Tasmane ou bien les sous-traitants payés au mois indépedemment de leur charge)")
    company_part_marging_amount_current = fields.Monetary('Marge sur dispo Tasmane (€) actuelle', store=True, compute=compute, help="Montant dispositif Tasmane - Coût de production dispo Tasmane") 
    company_part_marging_rate_current = fields.Float('Marge sur dispo Tasmane (%) actuelle', store=True, compute=compute)

    ######## OUTSOURCE PART
    outsource_part_amount_initial = fields.Monetary('Montant de la part sous-traitée initial', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte")
    outsource_part_cost_initial = fields.Monetary('Coût de revient de la part sous-traitée initial')
    outsource_part_marging_amount_initial = fields.Monetary('Marge sur part sous-traitée (€) initiale', store=True, compute=compute)
    outsource_part_marging_rate_initial = fields.Float('Marge sur part sous-traitée (%) initiale', store=True, compute=compute)

    outsource_part_amount_current = fields.Monetary('Montant de la part sous-traitée actuel', help="Montant produit par les sous-traitants de Tasmane : part produite par les sous-traitants que Tasmane paye à l'acte")
    outsource_part_cost_current = fields.Monetary('Coût de revient de la part sous-traitée actuel')
    outsource_part_marging_amount_current = fields.Monetary('Marge sur part sous-traitée (€) actuelle', store=True, compute=compute)
    outsource_part_marging_rate_current = fields.Float('Marge sur part sous-traitée (%) actuelle', store=True, compute=compute)
    #quid des co-traitants


    ######## OTHER PART
    other_part_amount_initial = fields.Monetary('Prix de vente HT autres prestations initial', help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_initial = fields.Monetary('Coût de revient HT des autres prestations initial')
    other_part_marging_amount_initial = fields.Monetary('Marge sur les autres prestations (€) initiale', store=True, compute=compute)
    other_part_marging_rate_initial = fields.Float('Marge sur les autres prestations (%) initiale', store=True, compute=compute)

    other_part_amount_current = fields.Monetary('Prix de vente HT des autres prestations actuel', help="Les autres prestations peuvent être la facturation d'un séminaire dans les locaux de Tasmane par exemple.")
    other_part_cost_current = fields.Monetary('Coût de revient HT des autres prestations actuel')
    other_part_marging_amount_current = fields.Monetary('Marge sur les autres prestations (€) actuelle', store=True, compute=compute)
    other_part_marging_rate_current = fields.Float('Marge sur les autres prestations (%) actuelle', store=True, compute=compute)
