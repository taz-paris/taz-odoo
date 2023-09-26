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


    employee_id = fields.Many2one('hr.employee', string="Tasmanien", ondelete='restrict', required=True)
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )
    name = fields.Char("Libellé", compute=_compute_name)

    period_goal = fields.Float("Objectif annuel")
