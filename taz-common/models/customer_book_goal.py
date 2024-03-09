from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime 

class tazCustomerBookGoal(models.Model):
    _name = "taz.customer_book_goal"
    _description = "Customer book goal"
    _order = "reference_period desc, industry_id"
    _sql_constraints = [
        ('partner_year_uniq', 'UNIQUE (industry_id, reference_period)',  "Impossible d'avoir deux objectifs différents pour le même compte et la même année.")
    ]

    @api.model
    def create(self, vals):
        if not vals.get("industry_id"):
            vals["industry_id"] = self._context.get("default_industry_id")
        return super().create(vals)

    @api.model
    def year_selection(self):
        year = 2019 # replace 2000 with your a start year
        year_list = []
        while year != datetime.date.today().year + 2: 
            year_list.append((str(year), str(year)))
            year += 1
        return year_list
    
    @api.model
    def year_default(self):
        y = datetime.date.today().year
        _logger.info(y)
        #self.reference_period = datetime.date.today().year
        return str(y)

    @api.depends('industry_id', 'reference_period')
    def _compute_name(self):
        for rec in self :
            rec.name =  "%s - %s" % (rec.reference_period or "", rec.industry_id.name or "") 


    industry_id = fields.Many2one('res.partner.industry', string="Compte", ondelete='restrict') #, required=True
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default,
        )
    name = fields.Char("Compte - Période", compute=_compute_name)

    book_followup_ids = fields.One2many('taz.customer_book_followup', 'customer_book_goal_id', string="Suivi du book")

    period_goal = fields.Float("Objectif annuel")
    #TODO remonter les valeur du customer_book_followup le plus réceent


class tazCustomerBookFollowup(models.Model):
    _name = "taz.customer_book_followup"
    _description = "Customer book evolution"
    _order = "date_update desc"
    _sql_constraints = [
        ('book_date_uniq', 'UNIQUE (customer_book_goal_id, date_update)',  "Impossible d'avoir suivis d'objectifs différents pour le même jour.")
    ]

    @api.depends('customer_book_goal_id', 'date_update', 'period_book', 'period_futur_book', 'period_goal')
    @api.model
    def landing(self):
        for record in self:
            _logger.info('==> LANDING')
            record.period_landing = record.period_book + record.period_futur_book
            record.period_delta = record.period_goal - record.period_landing
            if (record.period_goal and record.period_goal != 0.0):
                record.period_ratio = (record.period_landing / record.period_goal)*100.0
            else :
                record.period_ratio = 0.0

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        res['date_update'] = datetime.date.today()

        industry_default_id = self._context.get("default_industry_id")
        if industry_default_id:
            industry_default = self.env['res.partner.industry'].search([('id', '=', industry_default_id)])[0]
            bgl = self.env['taz.customer_book_goal'].search([('industry_id', '=', industry_default.id)], order="reference_period desc")
            if len(bgl)>0:
                bg_last = bgl[0]
                res['customer_book_goal_id'] = bg_last.id
                res['period_book'] = industry_default.get_book_by_year(int(bg_last.reference_period))

        _logger.info(res)
        return res

           

    #@api.model
    #def book_goal_id_default(self):
    #    partner_default = self._context.get("default_partner_id")
    #    if partner_default:
    #        bgl = self.env['taz.customer_book_goal'].search([('partner_id', '=', partner_default)], order="reference_period desc")
    #        if len(bgl)>0:
    #            return bgl[0].id
    #    return False 

    @api.depends('industry_id', 'date_update')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.industry_id.name or "", record.date_update or "") 

    name = fields.Char("Nom", compute=_compute_name)

    customer_book_goal_id = fields.Many2one('taz.customer_book_goal', string="Objectif annuel", required=True, readonly=False, ondelete='restrict')
    period_goal = fields.Float("Montant obj", related="customer_book_goal_id.period_goal", store=True)
    industry_id = fields.Many2one(related="customer_book_goal_id.industry_id", store=True)

    date_update = fields.Date("Date de valeur", readonly=True)
    period_book = fields.Float("Book à date", readonly=True)
    period_futur_book = fields.Float("Intime conviction", help="Montant que l'on estime pouvoir book en plus d'ici la fin de l'année.")

    period_landing = fields.Float("Atterissage annuel", compute=landing, store=True)
    period_delta = fields.Float("Delta aterrissage vs objectif", compute=landing, store=True)
    period_ratio = fields.Float("Ratio aterrissage vs objectif", compute=landing, store=True)
    comment = fields.Text("Commentaire")
    #TODO : ajouter des champ de delta par rapport au mois précédent

