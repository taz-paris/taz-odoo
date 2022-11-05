# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

import json

class tazBusinessAction(models.Model):
    _name = "taz.business_action"

    #@api.model
    #def default_get(self, fields):
    #    c = self.env.context.get('default_partner_id', None)
    #    c = 2664
    #    _logger.info(c)
    #    res = super().default_get(fields)
    #    res['user_id'] = 12
    #    res['partner_id']=c
        #if 'default_partner_id' in self._context:
        #    res['partner_id'] = self._context.get('default_partner_id')
    #    return res

    @api.model
    def create(self, vals):
        if not vals.get("partner_id"):
            vals["partner_id"] = self._context.get("default_partner_id")
        res = super().create(vals)
        if res :
            res.create_update_ms_planner_task([])
        return res

    def write(self, vals):
        _logger.info(vals)
        old_user_ids = self.user_ids
        res = super().write(vals)
        if res :
            self.create_update_ms_planner_task(old_user_ids)
        return res

    def get_ms_planner_plan_id(self):
        if not self.partner_id :
            raise ValidationError(_("Impossible de créer la tâche dans Microsoft Planner : vous n'avez pas asocié de contact à cette action commerciale."))
        if not self.parent_partner_id :
            raise ValidationError(_("Impossible de créer la tâche dans Microsoft Planner : le contact associé à cette action commerciale n'est rattaché à aucune entreprise."))
        if not self.parent_partner_industry_id :
            raise ValidationError(_("Impossible de créer la tâche dans Microsoft Planner : l'entreprise du contact associé à cette action commerciale n'est rattaché à aucun Business Domain."))
        if not self.parent_partner_industry_id.ms_planner_plan_id :
            raise ValidationError(_("Impossible de créer la tâche dans Microsoft Planner : le Business domaine de l'entreprise du contact associé à cette action commerciale n'au aucun ID de plan de rattachement."))
        return self.parent_partner_industry_id.ms_planner_plan_id

    @api.model
    def create_update_ms_planner_task(self, old_user_ids):
        _logger.info(self._context)
        if self._context.get('send_planner_req') == False :
            _logger.info('Ne pas envoyer la requete au planner')
            return False
        plan_id = self.get_ms_planner_plan_id()

        planner_assignments = {}
        #ajout d'un assignee

        for user in self.sudo().user_ids:
        #    _logger.info(user)
        #    _logger.info(user.oauth_uid)
            if user.oauth_uid != False :
                planner_assignments[user.oauth_uid] = dict({"@odata.type": "microsoft.graph.plannerAssignment", "orderHint": ' !'})
            else :
                raise ValidationError(_("Impossible d'enresgitrer la tâche : l'ID utilisateur Office365 de l'utilisateur affecté à cette tâche est inconnu (il ne s'est jamais connecté à Odoo via le SSO Office 365)."))
        #TODO : suppresion d'un assignee
            _logger.info("Anciens assignees %s" % old_user_ids)
            _logger.info("Actuels %s" % self.sudo().user_ids)
            for u in old_user_ids:
                if u not in self.sudo().user_ids:
                    if u.sudo().oauth_uid != False :
                        planner_assignments[u.sudo().oauth_uid] = None
                    else :
                        raise ValidationError(_("Impossible d'enresgitrer la tâche : l'ID utilisateur Office365 de l'utilisateur anciennement affecté à cette tâche est inconnu (il ne s'est jamais connecté à Odoo via le SSO Office 365)."))



        task = {
            "planId": plan_id,
            "title": self.name,
            "assignments": planner_assignments,
            "dueDateTime": str(self.date_deadline)
        }
        endpoint = "https://graph.microsoft.com/v1.0/planner/tasks"
        if self.ms_planner_task_data:
            #update the task
            task_id = None
            try :
                task_id = json.loads(self.ms_planner_task_data)['id']
            except TypeError:
                raise ValidationError(_("Impossible de mettre à jour la task sur planner : le champ ms_planner_task_data est défini mais mal formé"))
            endpoint+="/"+task_id
            ifmatch = json.loads(self.ms_planner_task_data)['@odata.etag'].replace("'W/", "").replace("'", "")
            req = self.env.user._msgraph_patch(endpoint, task, ifmatch)
        else :
            #create the task
            req = self.env.user._msgraph_post(endpoint, task)
        reponse = json.dumps(req)
        if reponse != 'null':
            self.with_context(send_planner_req=False).ms_planner_task_data=reponse
            

    #def get_ms_planner_task_delete(self):

    #def get_ms_planner_task_list(self):
    #    data = self.engtv.user._msgraph_get_planner_tasks(self.parent_partner_industry_id.ms_planner_plan_id)

            
    partner_id = fields.Many2one('res.partner', string="Contact", domain="[('is_company', '!=', True)]") #, required=True  
    parent_partner_id = fields.Many2one('res.partner', string="Entreprise", related='partner_id.parent_id', store=True)
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.parent_industry_id', store=True)

    name = fields.Char('Titre')
    note = fields.Text('Note')
    date_deadline = fields.Date('Echéance', index=True, required=True, default=fields.Date.context_today)
    user_ids = fields.Many2many(
        'res.users',
        'business_action_user_rel',
        'business_action_id',
        'user_id',
        string = 'Affectée à',
        default=lambda self: self.env.user,
        index=True,
        required=True,
        )
    state = fields.Selection([
        ('todo', 'À faire'),
        ('done', 'Fait'),
        ('wait', 'En attente')], 'Statut', default='todo')

    ms_planner_task_data = fields.Char("Data de la tâche M$ Planner")

    def open_record(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = self.id
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref("taz-common.business_action_form")

        # then open the form
        return {
                'type': 'ir.actions.act_window',
                'name': 'Action commerciale',
                'res_model': 'taz.business_action',
                'res_id': rec_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': form_id.id,
                'context': {},
                # if you want to open the form in edit mode direclty
                'flags': {'initial_mode': 'edit'},
                'target': 'current',
            }
