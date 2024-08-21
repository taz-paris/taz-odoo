from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime 
from dateutil.relativedelta import relativedelta

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

    @api.model
    def compute(self):
        for record in self:
            begin_year = datetime.datetime(int(record.reference_period), 1, 1) 
            end_year = datetime.datetime(int(record.reference_period), 12, 31)
            record.period_book, period_project_ids = record.industry_id.get_book_by_period(begin_year, end_year)

            record.period_delta = record.period_goal - record.period_book
            if (record.period_goal and record.period_goal != 0.0):
                record.period_ratio = (record.period_book / record.period_goal)*100.0
            else :
                record.period_ratio = 0.0
            record.book_last_month, last_month_project_ids = record.industry_id.get_book_by_period(datetime.datetime.today() + relativedelta(days=-31), datetime.datetime.today())
            record.number_of_opportunities, opportunities_project_ids = record.industry_id.get_number_of_opportunities()


    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        COMPUTED_FIELD_LIST = ['period_goal', 'period_book', 'period_ratio', 'period_delta', 'book_last_month', 'number_of_opportunities']
        for data in res:
            if '__domain' not in data.keys():
                continue

            customer_book_goals = self.search(data['__domain']).read(COMPUTED_FIELD_LIST)

            for computed_non_stored_field in COMPUTED_FIELD_LIST :
                data[computed_non_stored_field] = 0.0
                for book_goal in customer_book_goals:
                    data[computed_non_stored_field] += book_goal[computed_non_stored_field]

            data['period_ratio'] = 0.0
            if data['period_goal'] != 0.0:
                data['period_ratio'] = data['period_book']/data['period_goal'] * 100
            
            for computed_non_stored_field in COMPUTED_FIELD_LIST:
                if computed_non_stored_field not in fields:
                    del data[computed_non_stored_field]

        return res

    def action_open_project_opportunities(self):
        number_of_opportunities, opportunities_project_ids = self.industry_id.get_number_of_opportunities()
        view_id = self.env.ref("project_accounting.project_tree")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Avant-ventes du compte %s' % (self.industry_id.name),
                'res_model': 'project.project',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'target': 'current',
                'domain': [('id', 'in', opportunities_project_ids.ids)],
                'context' : {'no_create' : True},
            }

    def action_open_project_booked_last_month(self):
        book_last_month, last_month_project_ids = self.industry_id.get_book_by_period(datetime.datetime.today() + relativedelta(days=-31), datetime.datetime.today())
        view_id = self.env.ref("project_accounting.project_tree")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Prise de commande des 31 derniers jours du compte %s' % (self.industry_id.name),
                'res_model': 'project.project',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'target': 'current',
                'domain': [('id', 'in', last_month_project_ids.ids)],
                'context' : {'no_create' : True},
            }

    def action_open_project_booked_this_year(self):
        begin_year = datetime.datetime(int(self.reference_period), 1, 1)
        end_year = datetime.datetime(int(self.reference_period), 12, 31)
        period_book, period_project_ids = self.industry_id.get_book_by_period(begin_year, end_year)
        view_id = self.env.ref("project_accounting.project_tree")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Prise de commande sur l\'année %s du compte %s' % (self.reference_period, self.industry_id.name),
                'res_model': 'project.project',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'target': 'current',
                'domain': [('id', 'in', period_project_ids.ids)],
                'context' : {'no_create' : True},
            }

    industry_id = fields.Many2one('res.partner.industry', string="Compte", ondelete='restrict') #, required=True
    rel_business_priority = fields.Selection(related='industry_id.business_priority', store=True)
    reference_period = fields.Selection(
        year_selection,
        string="Année",
        default=year_default,
        )
    name = fields.Char("Compte - Période", compute=_compute_name)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)

    book_followup_ids = fields.One2many('taz.customer_book_followup', 'customer_book_goal_id', string="Suivi des objectifs")

    period_goal = fields.Monetary("Objectif annuel")

    period_book = fields.Monetary("Commande à date", compute=compute)
    period_delta = fields.Monetary("Delta objectif", compute=compute)
    period_ratio = fields.Float("Ratio objectif", compute=compute)
    book_last_month = fields.Monetary("Prise de commandes 31 derniers jours", compute=compute)
    number_of_opportunities = fields.Integer("Nombre d'avant-ventes", compute=compute)
    comment = fields.Text("Commentaire pour cette année")

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

        customer_book_goal = False

        #Utilisé pour le formulaire du res.parent.industry
        industry_default_id = self._context.get("default_industry_id")
        if industry_default_id:
            industry_default = self.env['res.partner.industry'].search([('id', '=', industry_default_id)])[0]
            bgl = self.env['taz.customer_book_goal'].search([('industry_id', '=', industry_default.id)], order="reference_period desc")
            if len(bgl)>0:
                bg_last = bgl[0]
                res['customer_book_goal_id'] = bg_last.id
                customer_book_goal = bg_last

        #Utilisé pour le formulaire du taz.customer_book_goal
        default_customer_book_goal_id = self._context.get("default_customer_book_goal_id")
        if default_customer_book_goal_id:
            res['customer_book_goal_id']  = default_customer_book_goal_id
            customer_book_goal = self.env['taz.customer_book_goal'].search([('id', '=', default_customer_book_goal_id)])[0]

        if customer_book_goal:
            begin_year = datetime.datetime(int(customer_book_goal.reference_period), 1, 1) 
            end_year = datetime.datetime(int(customer_book_goal.reference_period), 12, 31)
            res['period_book'], period_project_ids = customer_book_goal.industry_id.get_book_by_period(begin_year, end_year)

        _logger.info(res)
        return res

           
    @api.depends('industry_id', 'date_update')
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (record.industry_id.name or "", record.date_update or "") 

    name = fields.Char("Nom", compute=_compute_name)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)

    customer_book_goal_id = fields.Many2one('taz.customer_book_goal', string="Objectif annuel", required=True, readonly=False, ondelete='restrict')
    period_goal = fields.Monetary("Montant obj", related="customer_book_goal_id.period_goal", store=True)
    industry_id = fields.Many2one(related="customer_book_goal_id.industry_id", store=True)
    rel_business_priority = fields.Selection(related='industry_id.business_priority', store=True)

    date_update = fields.Date("Date de valeur", readonly=True)
    period_book = fields.Monetary("Prise de commande", readonly=True)
    period_futur_book = fields.Monetary("Intime conviction", help="Montant HT que l'on estime pouvoir prendre en commande en plus d'ici la fin de l'année.")

    period_landing = fields.Monetary("Atterissage annuel", compute=landing, store=True)
    period_delta = fields.Monetary("Delta aterrissage vs objectif", compute=landing, store=True)
    period_ratio = fields.Float("Ratio aterrissage vs objectif", compute=landing, store=True)
    comment = fields.Text("Commentaire")
