from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import re
import unicodedata

from odoo.addons import base

class eventRegistration(models.Model):
    _inherit = "event.registration"
    _rec_name = 'display_name'
    

    @api.onchange('mail_auto')
    def _onchange_mail_auto(self):
        _logger.info('-- _onchange_mail_auto')
        if self.mail_auto:
            self.contact_user_link_id = False

    @api.onchange('contact_user_link_id')
    def _onchange_contact_user_link_id(self):
        if self.contact_user_link_id:
            self.mail_auto = False
        last_office365_mail_draft = False


    mail_auto = fields.Boolean(string="Mail auto", default=True)
    contact_user_link_id = fields.Many2one("taz.contact_user_link", "Responsable de l'invitation", domain="[('partner_id', '=', partner_id)]")
    registration_user_id = fields.Many2one("res.users", "User", related="contact_user_link_id.user_id", store=True)
    state = fields.Selection(selection_add=[
            ('identified', 'Identifié'),
            ('draft', 'Invité'), ('cancel', 'Annulé'),
            ('open', 'Confirmé'), ('done', 'Présent')
            ], default='identified')
    last_office365_mail_draft = fields.Text("Structure JSON de la réponse Office365")
    event_id = fields.Many2one(states={'draft': [('readonly', False)], 'identified': [('readonly', False)]})
    comment = fields.Text("Commentaire", help="Ce commentaire est propre à l'inscription de ce contact pour cet évènement.")
    rel_partner_id_user_id = fields.Many2one(related='partner_id.user_id')



    def get_html_invitation(self):
        self.ensure_one()
        
        form = ""
        if self.contact_user_link_id.formality :
            if self.contact_user_link_id.formality in ['tu_prenom','vous_prenom'] :
                form = self.partner_id.first_name
            elif self.contact_user_link_id.formality == 'vous_nom' :
                if self.partner_id.title.name :
                    form = self.partner_id.title.name + ' ' + self.partner_id.name
      
        if not self.event_id.invitation_mail_template :
                raise ValidationError(_("Un administrateur du module Evènement doit définir le template du mail sur la fiche évènement."))

        template_xml_id = self.event_id.sudo().invitation_mail_template.get_metadata()[0].get('xmlid')
        if template_xml_id in [False, None, ""]:
            template_xml_id = self.event_id.sudo().invitation_mail_template.export_data(['id']).get('datas')[0][0]

        mail_body = self.env['ir.ui.view'].sudo()._render_template(template_xml_id, {
                'event': self.event_id,
                'registration' : self,
                'formality' : form,
                'closing' : self.registration_user_id.first_name + ' ' + self.registration_user_id.name
            })

        _logger.info(mail_body)

        return mail_body


    def create_office365_mail_draft(self):
        for rec in self :
            if self.env.user.id != rec.registration_user_id.id:
                raise ValidationError(_("Seul la personne responsable de l'invitation peut générer le brouillon sur sa boîte email."))

            mail_dict = {
                    "subject":"Invitation - " +  str(rec.event_id.name),
                    #"importance":"Low",
                    "body":{
                        "contentType":"HTML",
                        "content": self.get_html_invitation(),
                    },
                    "toRecipients":[
                        {
                            "emailAddress":{
                                "address": rec.partner_id.email,
                            }
                        }
                    ],
                }
            if rec.event_id.invitation_cc_address :
                mail_dict['ccRecipients'] = [
                        {
                            "emailAddress":{
                                "address": rec.event_id.invitation_cc_address,
                            }
                        }
                    ]
            office365_mail_draft = self.env.user._msgraph_post_draft_mail(mail_dict)
            rec.last_office365_mail_draft = office365_mail_draft
