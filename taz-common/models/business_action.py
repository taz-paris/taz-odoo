# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

import json

INTEGRATION_MS_PLANNER_ACTIVE = False

class tazBusinessAction(models.Model):
    _name = "taz.business_action"
    _description = "Record the futur and past business actions"
    _order = "date_deadline desc"
    _sql_constraints = [
        ('date_partner_uniq', 'UNIQUE (partner_id, date_deadline)',  "Impossible d'enregistrer deux actions commerciales le même jour pour le même client.")
    ]

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


# INITIALISATION du champ owner_id à partir du user_ids sur le stock d'actions
#        actions = self.env["taz.business_action"].search([])
#        for a in actions:
#            if len(a.user_ids) == 1:
#                a.owner_id = a.user_ids[0]

# RE-CALCUL de la date de dernière action faite des res.partner
#        partner_ids = self.env['res.partner'].search([('active', '=', True), ('is_company', '=', False), ('type', '=', 'contact')])._compute_date_last_business_action()

    @api.model
    def create(self, vals):
        if not vals.get("partner_id"):
            vals["partner_id"] = self._context.get("default_partner_id")
        res = super().create(vals)
        if res :
            if INTEGRATION_MS_PLANNER_ACTIVE :
                res.create_update_ms_planner_task([])
        return res

    def write(self, vals):
        old_user_ids = self.user_ids
        res = super().write(vals)
        if res :
            if INTEGRATION_MS_PLANNER_ACTIVE :
                self.create_update_ms_planner_task(old_user_ids)
        return res

    def unlink(self):
        if INTEGRATION_MS_PLANNER_ACTIVE :
            self.delete_ms_planner_task()
        res = super().unlink()

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

    def delete_ms_planner_task(self):
        endpoint = "https://graph.microsoft.com/v1.0/planner/tasks"
        if self.ms_planner_task_data:
            task_id = None
            try :
                task_id = json.loads(self.ms_planner_task_data)['id']
            except TypeError:
                raise ValidationError(_("Impossible de supprimer la tâche sur planner : le champ ms_planner_task_data est défini mais mal formé"))
            endpoint+="/"+task_id
            ifmatch = json.loads(self.ms_planner_task_data)['@odata.etag'].replace("'W/", "").replace("'", "")
            req = self.env.user._msgraph_delete(endpoint, ifmatch)


    def create_update_ms_planner_task(self, old_user_ids):
        _logger.info(self._context)
        if self._context.get('send_planner_req') == False :
            _logger.info('Ne pas envoyer la requete au planner')
            return False
        plan_id = self.get_ms_planner_plan_id()


        planner_assignments = {}
        #ajout d'un assignee
        for user in self.user_ids:
            if user.oauth_uid != False :
                planner_assignments[user.oauth_uid] = dict({"@odata.type": "microsoft.graph.plannerAssignment", "orderHint": ' !'})
            else :
                raise ValidationError(_("Impossible d'enresgitrer la tâche : l'ID utilisateur Office365 de l'utilisateur affecté à cette tâche est inconnu (il ne s'est jamais connecté à Odoo via le SSO Office 365)."))
        #TODO : suppresion d'un assignee
        for u in old_user_ids:
            if u not in self.user_ids:
                if u.oauth_uid != False :
                    planner_assignments[u.oauth_uid] = None
                else :
                    raise ValidationError(_("Impossible d'enresgitrer la tâche : l'ID utilisateur Office365 de l'utilisateur anciennement affecté à cette tâche est inconnu (il ne s'est jamais connecté à Odoo via le SSO Office 365)."))

        task = {
            "planId": plan_id,
            "title": self.name,
            "assignments": planner_assignments,
            "dueDateTime": str(self.date_deadline)
        }
        #task_detail = {
        #    'description' : self.note
        #}

        #action_id = Get action id opening your form
        #base_url = Url from system parameters
        #product_id = Id of product you want to get link to
        #link = '%s:8069/web/webclient/home#id=%s&view_type=form&title=Products&model=product.product&action_id=%s' % (base_url, product_id, action_id)

        #from odoo.http import request
        #check out/print:
        #request.httprequest.url

        endpoint = "https://graph.microsoft.com/v1.0/planner/tasks"
        if self.ms_planner_task_data:
            #update the task
            task_id = None
            try :
                task_id = json.loads(self.ms_planner_task_data)['id']
            except TypeError:
                raise ValidationError(_("Impossible de mettre à jour la tâche sur planner : le champ ms_planner_task_data est défini mais mal formé"))
            endpoint+="/"+task_id
            ifmatch = json.loads(self.ms_planner_task_data)['@odata.etag'].replace("'W/", "").replace("'", "")
            req = self.env.user._msgraph_patch(endpoint, task, ifmatch)
            #endpoint+="/details"
            #req_detail = self.env.user._msgraph_patch(endpoint, task_detail, ifmatch)
        else :
            #create the task
            req = self.env.user._msgraph_post(endpoint, task)
        reponse = json.dumps(req)
        if reponse != 'null':
            self.with_context(send_planner_req=False).ms_planner_task_data=reponse
            

    #def get_ms_planner_task_list(self):
    #    data = self.engtv.user._msgraph_get_planner_tasks(self.parent_partner_industry_id.ms_planner_plan_id)

            
    partner_id = fields.Many2one('res.partner', string="Contact", domain="[('is_company', '!=', True)]", ondelete='restrict') #, required=True  
    parent_partner_id = fields.Many2one('res.partner', string="Entreprise", related='partner_id.parent_id', store=True)
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Compte du parent', related='partner_id.parent_industry_id', store=True)

    name = fields.Char('Titre', required=True)
    note = fields.Text('Note')
    date_deadline = fields.Date('Échéance', index=True, required=False, default=fields.Date.context_today)
    owner_id = fields.Many2one('res.users', string='Affecté à', default=lambda self: self.env.user)
    user_ids = fields.Many2many(
        'res.users',
        'business_action_user_rel',
        'business_action_id',
        'user_id',
        string = 'Participants internes',
        default=lambda self: self.env.user,
        index=True,
        required=True,
        #domain=[('oauth_uid', '!=', False)]
        )
    state = fields.Selection([
        ('todo', 'À faire'),
        ('planned', 'Planifié'),
        ('done', 'Fait'),
        ('cancelled', 'Annulé'),
        ('wait', 'À replanifier')], 'Statut', default='todo', help="L'état doit être manuellement passé à Terminé une fois le client vu.")
    conclusion = fields.Selection([
        ('real_need', 'Besoin concret'),
        ('relation', 'Mise en relation'),
        ('next_rdv', 'Revoyure'),
        ('topic_identified', 'Sujet d\'intérêt identifié'),
        ('noting', 'Aucune suite à donner')
        ], "Conclusion")
    action_type = fields.Selection([
        ('regular_news', 'Intimité réseau'),
        ('commercial_interview', 'RDV commercial avec DM / en délégation'),
        ('propale', 'Contribution à une proposition commerciale'),
        ('first_meeting', 'Prise de connaissance/Découverte'),
        ('deepening', 'Approfondissement')
        ], "Type")
    report_url = fields.Char("URL vers le CR OneNote")

    ms_planner_task_data = fields.Char("Data de la tâche M$ Planner")
    is_rdv_to_be_taken_by_assistant = fields.Boolean("RDV à planifier par Executive Access")
    is_rdv_taken_by_assistant = fields.Boolean("RDV planifié par Executive Access")
    business_priority = fields.Selection(string='Niveau de priorité', related='parent_partner_id.business_priority', store=True)

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
