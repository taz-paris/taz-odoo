from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
import datetime
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
    _rec_name = "name"
    _description = "Record attributes of the relation of an user and a customer/contact"
    _sql_constraints = [
        ('contact_user_uniq', 'UNIQUE (partner_id, user_id)',  "Impossible d'enregistrer deux liens pour un même contact et un même utilisatuer.")
    ] 
    
    """
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        _logger.info("########################@")
        _logger.info(res)
        res['partner_id'] = self._context.get("default_partner_id")
        res['partner_id'] = self._context.get("default_partner_id")
        _logger.info(res)
        return res
        """

    def init_from_taggs(self):
        _logger.info("DEBUT init_from_taggs")
        #Fonction pour initialiser les ContactUserLink à partir des taggs pour les Voeux
        """
        for link in self.search([]):
            if link.communication_preference in ['email_tu', 'email_vous']:
                link.communication_preference = 'email_auto'
            if link.communication_preference in ['paper_tu', 'paper_vous']:
                link.communication_preference = 'paper_auto'
        for link in self.search([]):
            if link.communication_preference in ['email_tu', 'paper_tu']:
                link.formality = 'tu_prenom'
            if link.communication_preference in ['email_vous', 'paper_vous']:
                link.formality = 'vous_nom'
            if link.communication_preference in ['email_perso', 'paper_perso']:
                link.formality = 'vous_nom'
        """

        dict_tags = {
            'Voeux_ADU_email_perso' : {'user_id' : 6, 'communication_preference' : 'email_perso'},
            'Voeux_ADU_papier_perso' : {'user_id' : 6, 'communication_preference' : 'paper_perso'},
            'Voeux_ALE_email_perso' : {'user_id' : 85, 'communication_preference' : 'email_perso'},
            'Voeux_ALE_papier_perso' : {'user_id' : 85, 'communication_preference' : 'paper_perso'},
            'Voeux_DGE_email_perso' : {'user_id' : 20, 'communication_preference' : 'email_perso'},
            'Voeux_DGE_email_tu' : {'user_id' : 20, 'communication_preference' : 'email_tu'},
            'Voeux_DGE_email_vous' : {'user_id' : 20, 'communication_preference' : 'email_vous'},
            'Voeux_DGE_papier_perso' : {'user_id' : 20, 'communication_preference' : 'paper_perso'},
            'Voeux_EDV_email_perso' : {'user_id' : 24, 'communication_preference' : 'email_perso'},
            'Voeux_EDV_email_tu' : {'user_id' : 24, 'communication_preference' : 'email_tu'},
            'Voeux_EDV_papier_perso' : {'user_id' : 24, 'communication_preference' : 'paper_perso'},
            'Voeux_FBE_email_perso' : {'user_id' : 25, 'communication_preference' : 'email_perso'},
            'Voeux_FBE_papier_perso' : {'user_id' : 25, 'communication_preference' : 'paper_perso'},
            'Voeux_FJE_papier_perso' : {'user_id' : 19, 'communication_preference' : 'paper_perso'},
            'Voeux_FJE_papier_tu' : {'user_id' : 19, 'communication_preference' : 'paper_tu'},
            'Voeux_FJE_papier_vous' : {'user_id' : 19, 'communication_preference' : 'paper_vous'},
            'Voeux_FKO_email_perso' : {'user_id' : 13, 'communication_preference' : 'email_perso'},
            'Voeux_FKO_email_tu' : {'user_id' : 13, 'communication_preference' : 'email_tu'},
            'Voeux_FKO_email_vous' : {'user_id' : 13, 'communication_preference' : 'email_vous'},
            'Voeux_FKO_papier_perso' : {'user_id' : 13, 'communication_preference' : 'paper_perso'},
            'Voeux_IBN_email_perso' : {'user_id' : 97, 'communication_preference' : 'email_perso'},
            'Voeux_IBN_papier_perso' : {'user_id' : 97, 'communication_preference' : 'paper_perso'},
            'Voeux_JGA_email_perso' : {'user_id' : 14, 'communication_preference' : 'email_perso'},
            'Voeux_JLR_email_perso' : {'user_id' : 98, 'communication_preference' : 'email_perso'},
            'Voeux_JLR_papier_perso' : {'user_id' : 98, 'communication_preference' : 'paper_perso'},
            'Voeux_MAG_email_perso' : {'user_id' : 16, 'communication_preference' : 'email_perso'},
            'Voeux_MAG_papier_perso' : {'user_id' : 16, 'communication_preference' : 'paper_perso'},
            'Voeux_MBE_email_perso' : {'user_id' : 109, 'communication_preference' : 'email_perso'},
            'Voeux_MBE_papier_perso' : {'user_id' : 109, 'communication_preference' : 'paper_perso'},
            'Voeux_MJA_email_perso' : {'user_id' : 106, 'communication_preference' : 'email_perso'},
            'Voeux_MJA_papier_perso' : {'user_id' : 106, 'communication_preference' : 'paper_perso'},
            'Voeux_ONI_email_perso' : {'user_id' : 114, 'communication_preference' : 'email_perso'},
            'Voeux_ONI_papier_perso' : {'user_id' : 114, 'communication_preference' : 'paper_perso'},
            'Voeux_PDP_email_perso' : {'user_id' : 115, 'communication_preference' : 'email_perso'},
            'Voeux_PDP_papier_perso' : {'user_id' : 115, 'communication_preference' : 'paper_perso'},
            'Voeux_PDU_email_perso' : {'user_id' : 9, 'communication_preference' : 'email_perso'},
            'Voeux_PDU_papier_perso' : {'user_id' : 9, 'communication_preference' : 'paper_perso'},
            'Voeux_PGE_email_perso' : {'user_id' : 18, 'communication_preference' : 'email_perso'},
            'Voeux_PGE_email_tu' : {'user_id' : 18, 'communication_preference' : 'email_tu'},
            'Voeux_PGE_email_vous' : {'user_id' : 18, 'communication_preference' : 'email_vous'},
            'Voeux_PGE_papier_perso' : {'user_id' : 18, 'communication_preference' : 'paper_perso'},
            'Voeux_PLA_email_perso' : {'user_id' : 116, 'communication_preference' : 'email_perso'},
            'Voeux_PLA_papier_perso' : {'user_id' : 116, 'communication_preference' : 'paper_perso'},
            'Voeux_SRI_email_perso' : {'user_id' : 126, 'communication_preference' : 'email_perso'},
            'Voeux_SRI_papier_perso' : {'user_id' : 126, 'communication_preference' : 'paper_perso'},
            'Voeux_TMI_email_perso' : {'user_id' : 10, 'communication_preference' : 'email_perso'},
            'Voeux_TMI_email_tu' : {'user_id' : 10, 'communication_preference' : 'email_tu'},
            'Voeux_TMI_email_vous' : {'user_id' : 10, 'communication_preference' : 'email_vous'},
            'Voeux_TMI_papier_perso' : {'user_id' : 10, 'communication_preference' : 'paper_perso'},
            'Voeux_VVI_email_perso' : {'user_id' : 130, 'communication_preference' : 'email_perso'},
            'Voeux_VVI_papier_perso' : {'user_id' : 130, 'communication_preference' : 'paper_perso'},
            'Voeux_WTH_email_perso' : {'user_id' : 23, 'communication_preference' : 'email_perso'},
            'Voeux_WTH_papier_perso' : {'user_id' : 23, 'communication_preference' : 'paper_perso'},
        }

        for tag, dic in dict_tags.items() :
            _logger.info('======== '+tag)
            t = self.env['res.partner.category'].search([('name', '=', tag)])[0]
            for partner in t.partner_ids:
                contact_user_links = self.env['taz.contact_user_link'].search([('user_id', '=', dic['user_id']), ('partner_id', '=', partner.id)])
                if len(contact_user_links) == 0 :
                    _logger.info('lien manquant pour tag = %s / Contact = %s %s' % (tag, str(partner.id), partner.name))
                    #self.env['taz.contact_user_link'].create({'user_id' : dic['user_id'], 'partner_id' : partner.id, 'communication_preference' : dic['communication_preference']})
                #else:
                #    if contact_user_links[0].communication_preference == False :
                #        contact_user_links[0].communication_preference = dic['communication_preference']

        _logger.info("FIN init_from_taggs")



    @api.model
    def create(self, vals):
        if not vals.get("partner_id"):
            vals["partner_id"] = self._context.get("default_partner_id")
        return super().create(vals)

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
                    rec.next_meeting_before = passed_business_action[0].date_deadline + relativedelta(days=rec.target_contact_frequency_id.day_number)
                    if rec.next_meeting_before < datetime.date.today():
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


    @api.depends('partner_id.inhouse_influence_level')
    def _compute_rel_inhouse_influence_level(self):
        for rec in self :
            rec.rel_inhouse_influence_level = rec.partner_id.inhouse_influence_level

    def _inverse_rel_inhouse_influence_level(self):
        for rec in self :
            rec.partner_id.inhouse_influence_level = rec.rel_inhouse_influence_level


    @api.depends('user_id', 'partner_id')
    def _compute_name(self):
        for rec in self:
            p_name = ""
            if rec.partner_id.name_get() :
                p_name = rec.partner_id.name_get()[0][1]
            rec.name = rec.user_id.name_get()[0][1] + ' / ' + p_name


    name = fields.Char('Nom du lien', compute='_compute_name')
    user_id = fields.Many2one('res.users', string='Tasmanien', required=True, default=lambda self: self.env.user)

    partner_id = fields.Many2one('res.partner', string='Contact', required=False)
    parent_partner_id = fields.Many2one('res.partner', string="Entreprise", related='partner_id.parent_id', store=True)
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.parent_industry_id', store=True)
    rel_inhouse_influence_level = fields.Selection([
         ('1', "1 - Réseau - pas de lien direct"),
         ('2', "2 - Eclaireur - peut donner de l'information sur un compte à potentiel"),
         ('3', "3 - Prescripteur - peut pousser Tasmane vers un interlocuteur décideur"),
         ('4', "4 - Décideur -  peut décider par lui-même"),
         ], store=True, string="Niveau d'influence chez le client", compute="_compute_rel_inhouse_influence_level", inverse="_inverse_rel_inhouse_influence_level") 

    last_business_action_id = fields.Many2one('taz.business_action', string='Dernière action au statut FAIT', help="Dernière action commerciale au statut FAIT de ce tasmanien avec ce contact.", compute=_compute_date_business_action, store=True)
    date_last_business_action = fields.Date('Date dernière action au statut FAIT', compute=_compute_date_business_action, store=False)
    next_business_action_id = fields.Many2one('taz.business_action', string='Prochaine action', help="Prochaine action commerciale (quel que soit le statut) de ce tasmanien avec ce contact.", compute=_compute_date_business_action, store=True)
    is_late = fields.Boolean('En retard', help="La dernière action commerciale faite par ce tasmanien auprès de ce contact est plus ancienne que la fréquence souhaitée.", compute=_compute_date_business_action, store=True, default=False) #TODO :impossible de stocker la valeur de is_late car sa valeur reposer sur la date du jour
    next_meeting_before = fields.Date('À revoir avant le', compute=_compute_date_business_action, store=True)
    
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
