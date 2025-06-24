# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
                    
    
class tazMailActivity(models.Model):
     _inherit = "mail.activity"
     state = fields.Selection(selection_add=[('done', 'Terminée')])#, 'State', compute='_compute_state')
     is_done = fields.Boolean(string="Action terminée")
     partner_id = fields.Many2one('res.partner', string="Contact")#, domain="[('is_company', '=', 'False')]") 
     # on ne devrait avoir à créer ce champ
     # Dans l'idéal il faudrait surcharger le widget many2one_reference en s'inspirant du widget many2one mais c'est un peu compliqué
     # https://github.com/odoo/odoo/tree/16.0/addons/web/static/src/views/fields/many2one_reference
     # https://github.com/odoo/odoo/blob/16.0/addons/web/static/src/views/fields/many2one/many2one_field.js
     # https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/web/static/src/views/fields/relational_utils.js

     @api.onchange('partner_id', 'res_model')
     def _compute_res_id(self):
         for record in self :
             #if not partner_id :
             #   return True
             #if self.res_model :
             #   if self.res_model != 'res.partner':
             #       raise ValidationError("Opération impossible car l'objet ciblé par res.model n'est pas un res.partner.")
             #else :
             #   self.res_model = 'res.partner'
             self.res_model = 'res.partner'
             self.res_id = self.partner_id.id

     @api.depends('is_done')
     def _action_done(self, feedback=False, attachment_ids=None):
         self.is_done = True
         if feedback :
            if self.note :
                self.note = self.note + ' ' + feedback
            else :
                self.note = feedback
         #https://github.com/odoo/odoo/blob/16.0/addons/mail/models/mail_activity.py#L543 
         # Ne permettra plus de générer automatiquement l'activité suivante lorsque l'action est marquée done
         return [], []

     @api.depends('date_deadline')
     @api.onchange('is_done')
     def _compute_state(self):
         for record in self.filtered(lambda activity: activity.date_deadline):
             tz = record.user_id.sudo().tz
             date_deadline = record.date_deadline
             record.state = self._compute_state_from_date(date_deadline, tz)

     @api.model
     def _compute_state_from_date(self, date_deadline, tz=False):
         if self.is_done == True :
             return "done"
         return super()._compute_state_from_date(date_deadline, tz)
