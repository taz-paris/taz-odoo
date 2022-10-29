# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)



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
        return super().create(vals)
            
    partner_id = fields.Many2one('res.partner', string="Contact", domain="[('is_company', '!=', True)]") #, required=True  
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.industry_id')  #store=True

    name = fields.Char('Titre')
    note = fields.Text('Note')
    date_deadline = fields.Date('Echéance', index=True, required=True, default=fields.Date.context_today)
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    state = fields.Selection([
        ('todo', 'À faire'),
        ('done', 'Fait'),
        ('wait', 'En attente')], 'Statut', default='todo')

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
