from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

import datetime    

class employeeBookGoal(models.Model):
    _name = "project.employee_book_goal"
    _description = "Employee book goal"
    _order = "reference_period desc"
    _sql_constraints = [
        ('employee_year_uniq', 'UNIQUE (employee_id, reference_period)',  "Impossible d'avoir deux objectifs différents pour le même salarié et la même année.")
    ]
    _check_company_auto = True

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

    @api.depends('employee_id', 'reference_period')
    def _compute_name(self):
        for rec in self :
            rec.name =  "%s - %s %s" % (rec.reference_period or "", rec.employee_id.name or "", rec.employee_id.first_name or "") 

    def compute(self):
        for rec in self:
            distrib = self.env['project.book_employee_distribution_period'].search([('reference_period', '=', rec.reference_period), ('employee_id', '=', rec.employee_id.id)])
            period_book = 0.0
            for d in distrib:
                period_book += d.period_project_book_employee
            rec.period_book = period_book

            if rec.period_goal == 0.0:
                rec.period_rate = 0.0
            else :
                rec.period_rate = rec.period_book / rec.period_goal * 100.0

    employee_id = fields.Many2one('hr.employee', string="Collaborateur", ondelete='restrict', required=True, check_company=True)
    rel_job_id = fields.Many2one(related='employee_id.job_id', string="Grade", store=True, check_company=True)
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )
    name = fields.Char("Libellé", compute=_compute_name)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    period_goal = fields.Monetary("Objectif annuel")
    period_book = fields.Monetary("Book à date", compute=compute) #store=True
    period_rate = fields.Float("Ratio atteint/objectif", compute=compute)# , store=True)
