from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
import datetime
import json
from dateutil.relativedelta import relativedelta
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class ContactUserLinkFrequency(models.Model):
    _name = "taz.contact_user_link_frequency"
    _description = "Frequency of the relation of an user and a customer/contact"

    name = fields.Char("Libellé")
    day_number = fields.Integer("Nombre de jours")

class ContactUserLink(models.Model):
    _name = "taz.contact_user_link"
    _description = "Record attributes of the relation of an user and a customer/contact"
    _sql_constraints = [
        ('contact_user_uniq', 'UNIQUE (partner_id, user_id)',  "Impossible d'enregistrer deux liens pour un même contact et un même utilisateur.")
    ] 
    
    @api.depends('user_id', 'partner_id', 'partner_id.business_action_ids', 'partner_id.business_action_ids.date_deadline', 'partner_id.business_action_ids.state', 'target_contact_frequency_id', 'target_contact_frequency_id.day_number')
    def _compute_date_business_action(self):
        #_logger.info("-- _compute_date_business_action")
        for rec in self :
            partner_id = rec.partner_id
            #if rec._origin.id :
            #    partner_id = rec._origin
            #else:
            #    partner_id = rec.partner_id
            #_logger.info(partner_id)
            passed_business_action = rec.env['taz.business_action'].search(
               [
                   ('date_deadline', '<=', datetime.date.today()), 
                   ('state', '=', 'done'),
                   ('user_ids', 'in', rec.user_id.id),
                   ('partner_id', '=', partner_id.id),
               ], order="date_deadline desc")
            #_logger.info(passed_business_action)
            rec.is_late = False
            if len(passed_business_action):
                rec.last_business_action_id = passed_business_action[0]
                rec.date_last_business_action = passed_business_action[0].date_deadline
                if rec.target_contact_frequency_id :
                    next_meeting_before = passed_business_action[0].date_deadline + relativedelta(days=rec.target_contact_frequency_id.day_number)
                    if next_meeting_before < datetime.date.today():
                        rec.is_late = True
            else :
                rec.last_business_action_id = False
                rec.date_last_business_action = False
            future_business_action = rec.env['taz.business_action'].search(
               [
                   ('date_deadline', '>', datetime.date.today()), 
                   #('state', '=', 'done'),
                   ('user_ids', 'in', rec.user_id.id),
                   ('partner_id', '=', partner_id.id),
               ], order="date_deadline asc")
            if len(future_business_action):
                rec.next_business_action_id = future_business_action[0]
            else :
                rec.next_business_action_id = False

    @api.depends('date_last_business_action', 'next_meeting_before')
    def _compute_next_meeting_before(self):
        for rec in self:
            if rec.date_last_business_action and rec.target_contact_frequency_id :
                rec.next_meeting_before = rec.date_business_action + relativedelta(days=rec.target_contact_frequency_id.day_number)
            else :
                rec.next_meeting_before = False


    @api.depends('partner_id.inhouse_influence_level')
    def _compute_rel_inhouse_influence_level(self):
        for rec in self :
            rec.rel_inhouse_influence_level = rec.partner_id.inhouse_influence_level

    def _inverse_rel_inhouse_influence_level(self):
        for rec in self :
            rec.partner_id.inhouse_influence_level = rec.rel_inhouse_influence_level

    @api.depends('user_id', 'partner_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            p_name = ""
            if rec.partner_id :
                p_name = rec.partner_id.display_name
            rec.display_name = rec.user_id.display_name + ' / ' + p_name

    @api.depends('communication_preference', 'mail_template', 'last_office365_mail_draft')
    def compute_can_generate_office365_mail_draft(self):
        for rec in self :
            last_draft_date = False
            if rec.last_office365_mail_draft:
                last_draft_date = json.loads(rec.last_office365_mail_draft)
                if last_draft_date and 'createdDateTime' in last_draft_date.keys() :
                    last_draft_date = datetime.datetime.strptime(last_draft_date['createdDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                    last_draft_date = datetime.date(last_draft_date.year, last_draft_date.month, last_draft_date.day)
            if (rec.communication_preference not in ['email_perso', 'email_auto']) or (last_draft_date and (last_draft_date > datetime.date.today() + relativedelta(months=-2, day=1))) or (self.env.user.id != rec.user_id.id) or not rec.mail_template :
                rec.can_generate_office365_mail_draft = False 
            else :
                rec.can_generate_office365_mail_draft = True


    user_id = fields.Many2one('res.users', string='Collaborateur', required=True, default=lambda self: self.env.user)

    partner_id = fields.Many2one('res.partner', string='Contact', required=False)
    parent_partner_id = fields.Many2one('res.partner', string="Entreprise", related='partner_id.parent_id', store=True)
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.parent_industry_id', store=True)
    rel_inhouse_influence_level = fields.Selection([
         ('1', "1 - Réseau - pas de lien direct"),
         ('2', "2 - Eclaireur - peut donner de l'information sur un compte à potentiel"),
         ('3', "3 - Prescripteur - peut nous pousser vers un interlocuteur décideur"),
         ('4', "4 - Décideur -  peut décider par lui-même"),
         ], store=True, string="Niveau d'influence chez le client", compute="_compute_rel_inhouse_influence_level", inverse="_inverse_rel_inhouse_influence_level") 

    last_business_action_id = fields.Many2one('taz.business_action', string='Dernière action au statut FAIT', help="Dernière action commerciale au statut FAIT de ce collaborateur avec ce contact.", compute=_compute_date_business_action, store=False)
    next_business_action_id = fields.Many2one('taz.business_action', string='Prochaine action', help="Prochaine action commerciale (quel que soit le statut) de ce collaborateur avec ce contact.", compute=_compute_date_business_action, store=False)
    next_meeting_before = fields.Date('À revoir avant le', compute=_compute_next_meeting_before, store=True)
    is_late = fields.Boolean('En retard', help="La dernière action commerciale faite par ce collaborateur auprès de ce contact est plus ancienne que la fréquence souhaitée.", compute=_compute_date_business_action, store=False, default=False) #impossible de stocker la valeur de is_late car sa valeur reposer sur la date du jour (sauf à créer un traitement batch)
    date_last_business_action = fields.Date('Date dernière action au statut FAIT', compute=_compute_date_business_action, store=False)
    
    #RDV to plan before
    proximity_level = fields.Selection([
            ('0', "0 - je le connais de vue"),
            ('1', "1 - j'ai déjà travaillé avec lui"),
            ('2', "2 - j'ai eu une collaboration intense avec lui"),
            ('3', "3 - j'ai son numéro de portable et je peux l'appeler à 22h"),
        ], string="Niveau de proximité") 
    target_contact_frequency_id = fields.Many2one('taz.contact_user_link_frequency', string="Fréquence de contact")
    comment = fields.Text("Commentaire")
    formality = fields.Selection([
        ('vous_nom', 'Vous + nom'),
        ('vous_prenom', 'Vous + prénom'),
        ('tu_prenom', 'Tu + prénom'),
        ], "Tu/vous")
    communication_preference = fields.Selection([
            ('email_auto', "email auto"),
            ('email_perso', "email personalisé"),
            ('paper_auto', "papier auto"),
            ('paper_perso', "papier personalisé"),
        ], string="Pref. com. voeux") 
    mail_template = fields.Many2one('ir.ui.view', "Modèle mail voeux", domain=[('name', 'ilike', 'voeux'), ('type', '=', 'qweb')])
    last_office365_mail_draft = fields.Text("Structure JSON de la réponse Office365")
    can_generate_office365_mail_draft = fields.Boolean("Peut générer brouillon", compute=compute_can_generate_office365_mail_draft)
    mail_sent = fields.Boolean("Voeux envoyé", help="Case pouvant être cochée manuellement par l'utilsiateur une fois qu'il a envoyé le mail - pour faciliter le suivi.")


    def get_html_mail(self):
        self.ensure_one()
        
        form = ""
        if self.formality :
            if self.formality in ['tu_prenom','vous_prenom'] :
                form = self.partner_id.first_name
            elif self.formality == 'vous_nom' :
                if self.partner_id.title.name :
                    form = self.partner_id.title.name + ' ' + self.partner_id.name
      
        if not self.mail_template :
                raise ValidationError(_("Aucun template mail de voeux n'est défini pour ce lien Collaborateur-Contact. Vous devez en sélectionner un pour pouvoir générer un brouillon de mail."))

        template_xml_id = self.sudo().mail_template.get_metadata()[0].get('xmlid')
        if template_xml_id in [False, None, ""]:
            template_xml_id = self.sudo().mail_template.export_data(['id']).get('datas')[0][0]

        mail_body = self.env['ir.ui.view'].sudo()._render_template(template_xml_id, {
                'contact_user_link' : self,
                'target_year' : str(self.get_target_year()),
                'formality' : form,
                'closing' : self.user_id.first_name + ' ' + self.user_id.name
            })

        _logger.info(mail_body)

        return mail_body

    def get_target_year(self):
        today = datetime.date.today()
        if today.month > 6 :
            target_year = today.year + 1
        else :
            target_year = today.year
        return target_year

    def create_office365_mail_draft(self):
        for rec in self :
            if self.env.user.id != rec.user_id.id:
                raise ValidationError(_("Seul l'utilisateur responsable de l'invitation peut générer le brouillon sur sa boîte email."))

            mail_dict = {
                    "subject":"Meilleurs voeux " +  str(self.get_target_year()),
                    #"importance":"Low",
                    "body":{
                        "contentType":"HTML",
                        "content": self.get_html_mail(),
                    },
                    "toRecipients":[
                        {
                            "emailAddress":{
                                "address": rec.partner_id.email,
                            }
                        }
                    ],
                    "from" : {
                        "emailAddress":{
                            "address": self.env.user.login,
                        }
                    },
                    "sender" : {
                        "emailAddress":{
                            "address": self.env.user.login,
                        }
                    },
                }
            office365_mail_draft = self.env.user._msgraph_post_draft_mail(mail_dict)
            rec.last_office365_mail_draft = json.dumps(office365_mail_draft)
