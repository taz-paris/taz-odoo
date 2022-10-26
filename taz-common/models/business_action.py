# -*- coding: utf-8 -*-

from odoo import models, fields, api


class tazBusinessAction(models.Model):
    _name = "taz.business_action"
    partner_id = fields.Many2one('res.partner', string="Contact", required=True) #, domain="[('is_company', '=', False)]"
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.industry_id')  #store=True
    #activity_type_id = fields.Many2one(
    #    'mail.activity.type', string='Activity Type',
    #    domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]", ondelete='restrict',
    #    default=_default_activity_type)
    #activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
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
