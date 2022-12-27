from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class HrJob(models.Model):
    _inherit = "hr.job"

    def _get_daily_cost(self, date):
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

        return res.cost

    cost_ids = fields.One2many('hr.cost', 'job_id', string="CJM / TJM historisés")


class HrCost(models.Model):
    _name = "hr.cost"
    _description = "Cost history"
    _order = 'begin_date desc'

    _sql_constraints = [
        ('begin_date__uniq', 'UNIQUE (begin_date, job_id)',  "Impossible d'enregistrer deux objets pour le même poste et la même date d'effet.")
    ]

    def write(self, vals):
        if 'job_id' in vals.keys():
            raise ValidationError(_("Il est interdit de changer le poste d'une ligne de coût après sa création."))

        res = super().write(vals)

        if 'cost' in vals.keys():
            for account_analytic_line in account_analytic_line_ids:
                account_analytic_line.hr_cost_id = False #Cela va déclencher un recalcul de hr_cost_id et in fine du montant de la ligne

    ##TODO : ça ne suffit pas... notamment si on intercale une ligne de cout entre deux existantes...
            # si le job_id change : interdit, il est en readonly (simplificateur et pas génant fonctionellement) => OK
            # si cost change : recalculer toutes les account_analytics => OK
            # si la date change : reclaculer toutes ls account_analytics qui ont une date >= à la nouvelle date => TODO
            # à la création d'un HrCost : si la begin_date est antérieure à la begin_date d'un des hr_cost préexistant pour le job_id : reclaculer toutes ls account_alaitycs qui ont une date >= à la nouvelle date => TODO

    job_id = fields.Many2one('hr.job', string="Poste", required=True, readonly=True)
    begin_date = fields.Date("Date d'effet", required=True)
    cost = fields.Float("CJM", help="Coût journalier moyen imputé sur les lignes de pointage.", required=True)
    revenue = fields.Float("TJM", help="Taux journalier moyen HT vendu au client (prix catalogue).", required=True)

    account_analytic_line_ids = fields.One2many('account.analytic.line', 'hr_cost_id', string="Lignes de pointage")
