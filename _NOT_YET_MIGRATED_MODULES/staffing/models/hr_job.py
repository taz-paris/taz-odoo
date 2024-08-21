from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

import datetime

class HrJob(models.Model):
    _inherit = "hr.job"

    def _get_daily_cost_line(self, date):
        res = False
        for cost_line in self.cost_ids:
            if res == False :
                if cost_line.begin_date <= date:
                    res = cost_line
            else :
                if cost_line.begin_date <= date and cost_line.begin_date > res.begin_date:
                    res = cost_line

        if res == False :
            return False

        return res

    cost_ids = fields.One2many('hr.cost', 'job_id', string="CJM / TJM historisés")
    is_project_director = fields.Boolean("Peut être directeur de mission")


class HrCost(models.Model):
    _name = "hr.cost"
    _description = "Cost history"
    _order = 'begin_date desc'
    _check_company_auto = True

    _sql_constraints = [
        ('begin_date__uniq', 'UNIQUE (begin_date, job_id)',  "Impossible d'enregistrer deux objets pour le même poste et la même date d'effet.")
    ]

    def unlink(self):
        account_analytic_line_ids = self.account_analytic_line_ids
        super().unlink()
        for line in account_analytic_line_ids:
            line.refresh_amount()

    def create(self, vals):
        res = super().create(vals)
        for job in res:
            job.on_date_change(job.begin_date)

    def write(self, vals):
        if 'job_id' in vals.keys():
            raise ValidationError(_("Il est interdit de changer le poste d'une ligne de coût après sa création."))

        if 'begin_date' in vals.keys():
            old_begin_date = self.begin_date

        res = super().write(vals)

        if 'cost' in vals.keys():
            for account_analytic_line in self.account_analytic_line_ids:
                account_analytic_line.refresh_amount()

        if 'begin_date' in vals.keys():
            self.on_date_change(self.begin_date, old_begin_date)

    ## Gestion de la rétroactivité
            # si le job_id change : interdit, il est en readonly (simplificateur et pas génant fonctionellement) => OK
            # si cost change : recalculer toutes les account_analytics => OK
            # si la date change : reclaculer toutes ls account_analytics qui ont une date >= à la nouvelle date
            # à la création d'un HrCost : si la begin_date est antérieure à la begin_date d'un des hr_cost préexistant pour le job_id : reclaculer toutes ls account_alaitycs qui ont une date >= à la nouvelle date


    #TODO décliner la logique on_date_change sur l'objet hr.contract => à la création du contrat, au changement de contract.job_id ou au changement de date de début/fin du contrat => recalculer les lignes
    def on_date_change(self, new_date, former_date=False):
        pass
        """
        _logger.info("--- on_date_change")
        date_oldest = new_date
        if former_date : #s'il on est en train de créer un hr.cost, aucune former_date n'est fournie
            if former_date < date_oldest:
                date_oldest = former_date

        _logger.info(date_oldest)
        lines = self.env['account.analytic.line'].search([('date', '>=', date_oldest), ('project_id', '!=', False), ('holiday_id', '=', False)])

        _logger.info(len(lines))
        #TODO on pourrait borner la période de recherche dans le futur : bigin_date du hr.cost qui suit la date la plus récente entre l'ancienne et la nouvelle mais gain limité dans la plupart des cas
        for line in lines:
            job = line.employee_id._get_job_id(line.date)
            if not job:
                continue
            if job.id == self.job_id.id:
                line.refresh_amount()
        """

    def compute_end_date(self):
        for rec in self:
            end_date = False
            cost_lines = self.search([('job_id', '=', rec.job_id.id), ('begin_date', '>', rec.begin_date)], order="begin_date asc")
            if cost_lines:
                end_date = cost_lines[0].begin_date - datetime.timedelta(days=1)
            rec.end_date = end_date


    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    job_id = fields.Many2one('hr.job', string="Poste", required=True, check_company=True)
    begin_date = fields.Date("Date d'effet", required=True)
    end_date = fields.Date("Date de fin", compute=compute_end_date)
    cost = fields.Float("CJM", help="Coût journalier moyen imputé sur les lignes de pointage.", required=True)
    #daily_max_timesheet_unit_amount = field.Float("Pointage par jour", help="Exprimé suivant l'unité de pointage défini pour l'entreprise : jour ou heure")
    #weekly_max_timesheet_unit_amount = field.Float("Pointage par semaine", help="Exprimé suivant l'unité de pointage défini pour l'entreprise : jour ou heure")

    account_analytic_line_ids = fields.One2many('account.analytic.line', 'hr_cost_id', string="Lignes de pointage")
