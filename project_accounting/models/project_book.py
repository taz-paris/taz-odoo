from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

import datetime    

class projectBookPeriod(models.Model):
    _name = "project.book_period"
    _description = "Project book period"
    _order = "reference_period desc"
    _rec_name = "display_name"
    _sql_constraints = [
        ('project_year_uniq', 'UNIQUE (project_id, reference_period)',  "Impossible d'avoir deux book annuels différents pour un même projet.")
    ]

    def create(self,vals):
        #_logger.info("projectBookPeriod -- create")
        #_logger.info(vals)
        new = super().create(vals)
        for employee_distribution in new.project_id.book_employee_distribution_ids:
            self.env['project.book_employee_distribution_period'].sudo().create({'book_employee_distribution_id' : employee_distribution.id, 'project_book_period_id' : new.id})
        return new

    @api.model
    def year_selection(self):
        year = 2019 # replace 2000 with your a start year
        year_list = []
        while year != datetime.date.today().year +1 : 
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
        res = project.default_book_initial
            #TODO : pourquoi pas default_book_final ? Prendre default_book_cuurent s'il n'est pas nul ?
        for book_period in project.book_period_ids:
            if book_period.id == self.id :
                continue
            res -= book_period.period_project_book
        return res
        
    def compute_name(self):
        for rec in self:
            rec.display_name = rec.reference_period + " [" + str(rec.project_id.number) + "]"

    project_id = fields.Many2one('project.project', string="Projet", required=True, ondelete='cascade', default=_get_default_project_id)
    reference_period = fields.Selection(
        year_selection,
        string="Année de référence",
        default=year_default, # as a default value it would be 2019
        )

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    period_project_book = fields.Monetary('Book')#, default=_get_default_period_project_book)
    display_name = fields.Char('Name', compute=compute_name)


class projectBookEmployeeDistribution(models.Model):
    _name = "project.book_employee_distribution"
    _description = "Project book employee distribution"
    _sql_constraints = [
        ('project_employee_uniq', 'UNIQUE (project_id, employee_id)',  "Impossible d'avoir deux book différents pour un même salarié.")
    ]

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')


    def create(self,vals):
        new_list = super().create(vals)
        for new in new_list:
            for book_period in new.project_id.book_period_ids:
                self.env['project.book_employee_distribution_period'].create({'employee_id' : new.employee_id.id, 'book_employee_distribution_id' : new.id, 'project_book_period_id' : book_period.id})
        return new_list

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


class projectBookEmployeeDistributionPeriod(models.Model):
    _name = "project.book_employee_distribution_period"
    _description = "Project book employee distribution PERIOD"
    _sql_constraints = [
        ('proj_employ_period', 'UNIQUE (project_id, book_employee_distribution_id, project_book_period_id)',  "Impossible d'avoir deux book différents pour un même salarié/période.")
    ]

    def create(self,vals):
        _logger.info("Project book employee distribution PERIOD -- create")
        _logger.info(vals)
        new = super().create(vals)
        return new

    @api.constrains('book_employee_distribution_id', 'book_period_id')
    def _check(self):
         for rec in self :
             if not(rec.book_employee_distribution_id.project_id.id) or not(rec.project_book_period_id.project_id.id) :
                raise ValidationError(_('Le book_employee_distribution_id et project_book_period_id doivent être renseignés.'))
             if rec.book_employee_distribution_id.project_id.id != rec.project_book_period_id.project_id.id :
                raise ValidationError(_('Le book_employee_distribution_id et project_book_period_id ne sont pas rattachés au même projet.'))


    @api.depends('book_employee_distribution_id', 'project_book_period_id', 'book_factor', 'period_project_book', 'rel_is_book_manually_computed')
    def compute(self):
        for rec in self :
            if rec.rel_is_book_manually_computed == False :
                rec.period_project_book_employee = rec.book_factor * rec.period_project_book

    # Stored data
    book_employee_distribution_id = fields.Many2one('project.book_employee_distribution', ondelete='cascade')
    project_book_period_id = fields.Many2one('project.book_period', required=True, ondelete='cascade')

    # Computed data
    period_project_book_employee = fields.Monetary("Book pour l'année/projet/employé", compute=compute, store=True, group_operator='sum')

    # Related book_employee_distribution_id
    employee_id = fields.Many2one('hr.employee', related='book_employee_distribution_id.employee_id', required=True, readonly=False, string="Employé", store=True)
    book_factor = fields.Float(related="book_employee_distribution_id.book_factor", string="Coef. pour le projet/année/employée", store=True, group_operator=False)

    # Related project_book_period_id
    project_id = fields.Many2one('project.project', related='project_book_period_id.project_id', string="Projet", store=True)
    reference_period = fields.Selection(related='project_book_period_id.reference_period', store=True)
    company_id = fields.Many2one('res.company', related="project_book_period_id.company_id")
    currency_id = fields.Many2one('res.currency', related="project_book_period_id.currency_id")
    period_project_book = fields.Monetary(related="project_book_period_id.period_project_book", string="Book du projet pour l'année", store=True, readonly=False, group_operator=False)
    rel_book_comment = fields.Text(related='project_id.book_comment')
    rel_is_book_manually_computed = fields.Boolean(related="project_id.is_book_manually_computed")
