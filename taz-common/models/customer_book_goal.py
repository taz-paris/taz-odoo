# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime    

class tazCustomerBookGoal(models.Model):
    _name = "taz.customer_book_goal"
    _sql_constraints = [
        ('partner_year_uniq', 'UNIQUE (partner_id, reference_period)',  "Impossible d'avoir deux objectifs différents pour la même entreprise et la même année.")
    ]

    @api.model
    def create(self, vals):
        if not vals.get("partner_id"):
            vals["partner_id"] = self._context.get("default_partner_id")
        return super().create(vals)

    @api.model
    def year_selection(self):
        year = 2019 # replace 2000 with your a start year
        year_list = []
        while year != datetime.date.today().year + 2: # replace 2030 with your end year
            year_list.append((str(year), str(year)))
            year += 1
        return year_list
    
    @api.model
    def year_default(self):
        y = datetime.date.today().year
        _logger.info(y)
        #self.reference_period = datetime.date.today().year
        return str(y)

    @api.depends('partner_id', 'reference_period')
    def _compute_name(self):
        self.name =  "%s - %s" % (self.partner_id.name or "", self.reference_period or "") 

    partner_id = fields.Many2one('res.partner', string="Entreprise", domain="[('is_company', '=', True)]") #, required=True
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.industry_id')  #store=True
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        size=4
        )
    name = fields.Char("Entreprise - Période", compute=_compute_name)

    book_followup_ids = fields.One2many('taz.customer_book_followup', 'customer_book_goal_id', string="Suivi du book")

    period_goal = fields.Float("Objectif annuel")
    #TODO remonter les valeur du customer_book_followup le plus réceent


class tazCustomerBookFollowup(models.Model):
    _name = "taz.customer_book_followup"
    _sql_constraints = [
        ('book_date_uniq', 'UNIQUE (customer_book_goal_id, date_update)',  "Impossible d'avoir suivis d'objectifs différents pour le même jour.")
    ]

    @api.depends('customer_book_goal_id', 'date_update', 'period_book', 'period_futur_book')
    @api.model
    def landing(self):
        for record in self:
            record.period_landing = record.period_book + record.period_futur_book
            record.period_delta = record.period_goal - record.period_landing
            if (record.period_landing and record.period_landing != 0.0):
                record.period_ratio = (record.period_landing / record.period_goal)*100.0
            else :
                record.period_ratio = 0.0

    @api.model
    def date_default(self):
        return datetime.date.today()

    @api.model
    def book_goal_id_default(self):
        partner_default = self._context.get("default_partner_id")
        if partner_default:
            bgl = self.env['taz.customer_book_goal'].search([('partner_id', '=', partner_default)], order="reference_period desc")
            if len(bgl)>0:
                return bgl[0].id
        return False 

    @api.depends('partner_id', 'date_update')
    def _compute_name(self):
        self.name = "%s - %s" % (self.partner_id.name or "", self.date_update or "") 

    name = fields.Char("Nom", compute=_compute_name)

    customer_book_goal_id = fields.Many2one('taz.customer_book_goal', string="Objectif annuel", required=True, default=book_goal_id_default)
    period_goal = fields.Float("Montant obj", related="customer_book_goal_id.period_goal", store=True)
    partner_id = fields.Many2one(string="Entreprise", related="customer_book_goal_id.partner_id", store=True)

    date_update = fields.Date("Date de valeur", default=date_default)
    period_book = fields.Float("Book à date")
    period_futur_book = fields.Float("Intime conviction", help="Montant que l'on estime pouvoir book en plus d'ici la fin de l'année.")

    period_landing = fields.Float("Atterissage annuel", compute=landing)
    period_delta = fields.Float("Delta aterrissage vs objectif", compute=landing)
    period_ratio = fields.Float("Ratio aterrissage vs objectif", compute=landing)
    comment = fields.Text("Commentaire")
    #TODO : ajouter des champ de delta par rapport au mois précédent

