# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime    

class tazCustomerBookGoal(models.Model):
    _name = "taz.customer_book_goal"
    _sql_constraints = [
        ('partner_year_uniq', 'UNIQUE (partner_id, reference_period)',  "Impossible d'avoir deux objectifs différent pour la même entreprise et la même année.")
    ]

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
        return datetime.date.today().year

    @api.depends('partner_id', 'reference_period')
    def _compute_name(self):
        self.name =  "%s - %s" % (self.partner_id.name or "", self.reference_period or "") 

    partner_id = fields.Many2one('res.partner', string="Entreprise", domain="[('is_company', '=', True)]") #, required=True
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.industry_id')  #store=True
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )
    name = fields.Char("Entreprise - Période", compute=_compute_name)

    book_followup_ids = fields.One2many('taz.customer_book_followup', 'customer_book_goal_id', string="Suivi du book")

    period_goal = fields.Float("Objectif annuel")


class tazCustomerBookFollowup(models.Model):
    _name = "taz.customer_book_followup"

    @api.model
    def landing(self):
        self.period_landing = self.period_book + self.period_futur_book
        self.period_delta = self.period_goal - self.period_landing
        #if (self.period_landing and self.period_landing != 0):
        #    self.period_ratio = self.period_landing / self.period_goal

    @api.model
    def date_default(self):
        return datetime.date.today()

    @api.model
    def book_goal_id_default(self):
        return False #TODO si j'ajoute une ligne depuis la fiche entreprise, passer l'id partner en contexte et récupérer l'objet customer_book_goal_id le plus récent

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
    period_delta = fields.Float("Delta", compute=landing)
    #period_ratio = fields.Float("Ratio aterrissage vs objectif", compute=landing)
    comment = fields.Text("Commentaire")

