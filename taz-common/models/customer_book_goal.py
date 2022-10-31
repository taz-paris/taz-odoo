# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime    

class tazCustomerBookGoal(models.Model):
    _name = "taz.customer_book_goal"

    @api.model
    def year_selection(self):
        year = 2019 # replace 2000 with your a start year
        year_list = []
        while year != datetime.date.today().year + 2: # replace 2030 with your end year
            year_list.append((str(year), str(year)))
            year += 1
        return year_list
    
    @api.model
    def year_default(self)
        return datetime.date.today().year

    @api.model
    def landing(self)
        self.period_landing = self.period_book + self.periode_futur_book
        self.periode_delta = self.period_goal - self.period_landing
        self.periode_ratio = self.period_landing / self.period_landing

    partner_id = fields.Many2one('res.partner', string="Contact", domain="[('is_company', '=', True)]") #, required=True
    parent_partner_industry_id = fields.Many2one('res.partner.industry', string='Secteur du parent', related='partner_id.industry_id')  #store=True
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )
    date_update = fields.Date("Date de valeur")
    period_goal = fields.Float("Objectif annuel")
    period_book = fields.Float("Book à date")
    periode_futur_book = fields.Float("Intime conviction", help="Montant que l'on estime pouvoir book en plus d'ici la fin de l'année.")
    periode_landing = fields.Float("Atteriassage annuel", compute=landing)
    periode_delta = fields.Float("Delta", compute=landing)
    periode_ratio = fields.Float("Ratio aterrissage vs objectif", compute=landing)
    comment = fields.text("Commentaire")
