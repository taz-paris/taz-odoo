from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

import datetime    

class projectBookPeriod(models.Model):
    _name = "project.book_period"
    _description = "Project book period"
    _order = "reference_period desc"
    _sql_constraints = [
        ('project_year_uniq', 'UNIQUE (project_id, reference_period)',  "Impossible d'avoir deux book annuels différents pour un même projet.")
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

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    def _get_default_period_project_book(self):
        _logger.info("---_get_default_period_project_book")
        project = self.env['project.project'].browse(self._get_default_project_id())
        res = project.default_book
        _logger.info(res)
        for book_period in project.book_period_ids:
            if book_period.id == self.id :
                continue
            res -= book_period.period_project_book
        _logger.info(res)
        return res
        

    project_id = fields.Many2one('project.project', string="Projet", required=True, default=_get_default_project_id, ondelete='cascade')
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    period_project_book = fields.Monetary('Book', default=_get_default_period_project_book)


class projectBookEmployeeDistribution(models.Model):
    _name = "project.book_employee_distribution"
    _description = "Project book employee distribution"
    _sql_constraints = [
        ('project_employee_uniq', 'UNIQUE (project_id, employee_id)',  "Impossible d'avoir deux book différents pour un même salarié.")
    ]

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')


    @api.constrains('book_factor')
    def _check_book_factor(self):
        for record in self:
            #TODO : rendre les bornes des contrôles paramétrables
            if record.book_factor > 1.0 or record.book_factor < 0.0:
                raise ValidationError("Le coefficient de book doit être compris entre 0 et 1 pour chaque salarié.")

            total_book_factor = 0.0
            for book_employee_distribution in record.project_id.book_employee_distribution_ids:
                total_book_factor += book_employee_distribution.book_factor
            if total_book_factor > 2.0 or total_book_factor < 0.0:
                raise ValidationError("La somme des coefficients de book attribués dans un projet doit être comprise entre 0 et 2.")


    employee_id = fields.Many2one('hr.employee', domain=[('active', '=', True)], string="Salarié")
    project_id = fields.Many2one('project.project', string="Projet", required=True, default=_get_default_project_id, ondelete='cascade')
    book_factor = fields.Float("Coefficient", required=True)
