from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
from odoo.tools import float_round

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def write(self, vals):
        if 'staffing_need_id' in vals.keys():
            vals = self._sync_project(vals)
        if 'project_id' in vals.keys() and 'account_id' not in vals.keys():
            vals['account_id'] = self.env['project.project'].browse([vals['project_id']])[0].analytic_account_id.id
        #_logger.info(vals)
        res = super().write(vals)
        if 'amount' in vals.keys() or 'unit_amount' in vals.keys(): #TODO : contrôler si elle change de date ou de catégorie ?
            self.check_accounting_closed()
        return res

    @api.model
    def create(self, vals):
        res = self._sync_project(vals)
        res = super().create(res)
        res.check_accounting_closed()
        return res

    def check_accounting_closed(self):
        for rec in self :
            if rec.category in ['project_employee_validated', 'project_forecast']: #les changements sont possibles a postériori pour les timesheet liées aux congés
                company = rec.env['res.company'].browse(rec.company_id.id)[0]
                if company.fiscalyear_lock_date and (company.fiscalyear_lock_date > rec.date):
                    if rec.category == 'project_employee_validated' :
                        raise ValidationError(_("Une écriture analytique de la catégorie Pointage ne peut être créée ou changer de nombre de jours/valorisation après la clôture comptable. : %s" % str(rec.read())))
                    elif rec.category == 'project_forecast' :
                        _logger.info("Cette écriture analytique de type PREVISIONNEL a changé de montant/unit_amount après la date de cloture comptable : %s" % str(rec.read()))

    def unlink(self):
        self.check_accounting_closed()
        return super().unlink()

    def _sync_project(self, vals):
        #_logger.info('---------- _sync_project account.analytic.line account_analytic_line.py')
        #_logger.info(vals)
        #TODO : si le projet change, changer le staffing_need_id
        if 'staffing_need_id' not in vals:
            #Notamment dans le cas de la créetion d'une ligne issue d'un congés
            return vals

        #_logger.info(vals)
        need_id = vals['staffing_need_id']
        needs = self.env['staffing.need'].browse([need_id])
        need = needs[0]

        vals['project_id'] = need.project_id.id
        vals['account_id'] = need.project_id.analytic_account_id.id
        vals['employee_id'] =  need.staffed_employee_id.id
        return vals

    def compute_period_amounts(self):
        #_logger.info('---------- compute_period_amounts >> account_analytic_line.py')
        for line in self :
            date_start = self.env.context.get('period_date_start')
            date_end = self.env.context.get('period_date_end')
            #_logger.info('%%%% context_date_start' + str(date_start))
            #_logger.info('%%%% context_date_end' + str(date_end))

            if not(date_start) or not(date_end):
                line.period_unit_amount = 0
                line.period_amount = 0
                continue

            date_start = datetime.strptime(str(date_start), '%Y-%m-%d').date()
            date_end = datetime.strptime(str(date_end), '%Y-%m-%d').date()

            line.period_unit_amount, line.period_amount = line.compute_period_amounts_raw(date_start, date_end)


    def compute_period_amounts_raw(self, date_start, date_end):
            line = self

            
            if not date_start and not date_end :
                period_unit_amount = line.unit_amount
                period_amount = line.amount
                return period_unit_amount, period_amount 


            if date_start > date_end :
                raise ValidationError(_("Start date should be <= end date"))

            if line.date >= date_start and (not line.date_end or line.date_end <= date_end):
                period_unit_amount = line.unit_amount
                period_amount = line.amount
                return period_unit_amount, period_amount 

            line_date_end = line.date_end
            if not line_date_end :
                line_date_end = line.date
            work_days_line = line.employee_id.sudo().number_work_days_period(line.date, line_date_end)
            work_days_line_in_period = line.employee_id.sudo().number_work_days_period(max(line.date, date_start), min(line_date_end, date_end))
            #_logger.info('work_days_line %s' % work_days_line)
            #_logger.info('work_days_line_in_period %s' % work_days_line_in_period)
            #_logger.info('line.unit_amount %s' % line.unit_amount)

            if work_days_line != 0:
                period_unit_amount = work_days_line_in_period/work_days_line * line.unit_amount 
                period_amount = work_days_line_in_period/work_days_line * line.amount
            else : 
                period_unit_amount = 0
                period_amount = 0
            return period_unit_amount, period_amount 


    category = fields.Selection(selection_add=[
            ('project_forecast', 'Prévisionnel'), 
            ('project_employee_validated', 'Pointage (validé ou non)'),
        ])

    staffing_need_id = fields.Many2one('staffing.need', ondelete="set null") # On delete is "set null" and not "restrict" because on Napta (and Odoo native), a timesheet is linked to a project, so the staffing need can be deleted without the timesheet (but a userperiod has to be linked to a stafffing need)
    rel_project_staffing_aggregation = fields.Selection(related='project_id.staffing_aggregation', store=True)
    hr_cost_id = fields.Many2one('hr.cost', ondelete="restrict")
    employee_job_id = fields.Many2one(string="Grade", related='employee_id.job_id')
    date_end = fields.Date("Date de fin")

    period_unit_amount = fields.Float("J. période", group_operator='sum', help="Nombre de jours affectés à la période passée en contexte, 0 si aucune période n'est transmise en context.", digits=(18,8), compute=compute_period_amounts)
    period_amount = fields.Float("Montant période", group_operator='sum', help="Valorisation en € des jours affectés à la période passée en contexte, 0 si aucune période n'est transmise en context.", digits=(13,3), compute=compute_period_amounts)
          

    def get_timesheet_grouped(self, pivot_date, date_start=None, date_end=None, filters=None):
        # Cette fonction force les date de début/fin à un lundi/dimanche pour éviter de couper les semaines, notamment car le prévisionné est enregistré à la semaine
        date_start_monday = None
        date_end_sunday = None
 
        if date_start and date_end :
            if date_start > date_end :
                raise ValidationError(_("Start date should be <= end date"))

        if date_start:
            date_start_substracted_days = date_start.weekday()
            date_start_monday = date_start - timedelta(days=date_start_substracted_days)
        if date_end :
            date_end_added_days = 6-date_end.weekday()
            date_end_sunday = date_end + timedelta(days=date_end_added_days)

        monday_pivot_date =  pivot_date - timedelta(days=pivot_date.weekday())

        return self.get_timesheet_grouped_raw(monday_pivot_date, date_start=date_start_monday, date_end=date_end_sunday, filters=filters)


    def get_timesheet_grouped_raw(self, pivot_date, date_start=None, date_end=None, filters=None):
        #_logger.info('------ get_timesheet_grouped_raw date_start=%s, date_end=%s' % (date_start, date_end))
        # Usage de cette fonction :
        #   - Calculer le temps pointé / prévisionnel d'un consultant
        #   - Calculer la disponibilité d'un consultant sur une période (passé, présente ou future)

        # Modèle de données :
        #   - La base de données stock des lignes analytic différentes pour le pointage réalisé et le prévisionnel, qui sont conservées en parallèle dans le temps
        #   - Le prévisionnel possède une date de fin : il est souvent exprimé à la semaine sur Napta mais posséder n'importe quelle date de début et de fin
        #           # Donc sa période peut être à cheval sur plusieurs semaine/mois/années.
        #   - Le pointé est toujours exprimé sur un jour précis
        #   - Les demandes de congés validées sont converties en pointage à la maille de la journée par Odoo

        #TODO : interdire de modifier le prévisionnel après la fin de la semaine
        #TODO : interdire d'avoir plus d'une ligne d'une catégorie, d'un projet / tesk et d'un employé par date
        #TODO : passer le pointage à validé pour toute la semaine et tous les projets en même temps
        #TODO : interdire les affectations hors de la période du projet => ATTENTION : c'est autorisé sur Fitnet donc risque de blocage
                # En revanche : laisser la possibilité de pointer après la date de fin de l'affectation initiale, sinon ça ne sera pas pratique


        if date_start and date_end :
            if date_start > date_end :
                raise ValidationError(_("Start date should be <= end date"))

        dic = [
                ('employee_id', '!=', False),
                ('project_id', '!=', False),
                ('category', 'in', ['project_forecast', 'project_employee_validated', 'other']),
                ('rel_project_staffing_aggregation', '!=', False),
              ]

        if date_end :
            dic.append(('date', '<=', date_end))
        if date_start:
            dic += ['|', '&', ('date_end', '=', False), ('date_end', '>=', date_start), ('date', '>=', date_start)]

        if filters:
            for condition in filters:
                if condition[0] in ['category', 'date']:
                    raise ValidationError(_('Valeur interdite dans le filtre : %s' % condition[0]))
                dic.append(condition)
        timesheets = self.env['account.analytic.line'].search(dic)

        pivot_date = pivot_date.date()

        aggreation = {}
        #### first level = project taffing_aggregation
        ###### second level = timesheet.category
        ######## third level = list of timesheets / sum_period_unit_amount, sum_period_amount
        for aggregation_key in dict(self.env['project.project']._fields['staffing_aggregation'].selection).keys():
                aggreation[aggregation_key] = {}
                for category_key in dict(self.env['account.analytic.line']._fields['category'].selection).keys():
                    aggreation[aggregation_key][category_key] = {
                            'timesheet_ids' : [],
                            'sum_period_unit_amount' : 0.0,
                            'sum_period_amount' : 0.0,
                        }
            
        for timesheet in timesheets:
            if timesheet.encoding_uom_id.id != self.env.ref("uom.product_uom_day").id:
                # L'encoding_uom_id n'est pas stocké, donc on ne peut pas le mettre dans le filtre de la requête SQL
                continue

            agg = aggreation[timesheet.rel_project_staffing_aggregation]
            agg[timesheet.category]['timesheet_ids'] += timesheet

            period_unit_amount, period_amount = timesheet.compute_period_amounts_raw(date_start, date_end)
            agg[timesheet.category]['sum_period_unit_amount'] += period_unit_amount
            agg[timesheet.category]['sum_period_amount'] += period_amount

        res = {
                'pivot_date' : pivot_date,
                'start_date' : date_start,
                'end_date' : date_end,
                'aggreation_by_project_type' : aggreation,
              }
        return res


    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        #_logger.info('======================= read_group account_analytic_line.py')
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'period_unit_amount' in fields or 'period_amount' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    if 'period_unit_amount' in fields:
                        period_unit_amount = 0.0
                        for record in lines:
                            period_unit_amount += record.period_unit_amount
                        line['period_unit_amount'] = period_unit_amount

                    if 'period_amount' in fields:
                        period_amount = 0.0
                        for record in lines:
                            period_amount += record.period_amount
                        line['period_amount'] = period_amount
        return res

    #override to deal with uom in days
    #odoo/addons/hr_timesheet/models/hr_timesheet.py
    def _timesheet_postprocess_values(self, values):
        """ Get the addionnal values to write on record
            :param dict values: values for the model's fields, as a dictionary::
                {'field_name': field_value, ...}
            :return: a dictionary mapping each record id to its corresponding
                dictionary values to write (may be empty).
        """
        result = {id_: {} for id_ in self.ids}
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        # (re)compute the amount (depending on unit_amount, employee_id for the cost, and account_id for currency)
        #_logger.info('-- _timesheet_postprocess_values')
        if any(field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id', 'encoding_uom_id', 'holiday_id']):
            if 'amount' in values or 'hr_cost_id' in values:
                return result #sinon boucle infinie

            for timesheet in sudo_self:
                amount_converted, cost_line = timesheet.compute_amount()
                #if not amount_converted:
                #    continue
                result[timesheet.id].update({
                    'amount': amount_converted,
                    'hr_cost_id' : cost_line,
                })
        #_logger.info(result)
        return result
    



    def compute_amount(self):
        timesheet = self

        if not self.employee_id :
            return False,False
        
        if timesheet.holiday_id :
            return False,False

        encoding_uom_id = self.encoding_uom_id

        if encoding_uom_id == self.env.ref("uom.product_uom_hour"):
            cost = timesheet._hourly_cost()
            cost_line = False
        elif encoding_uom_id == self.env.ref("uom.product_uom_day"):
            cost, cost_line = timesheet.employee_id._get_daily_cost(timesheet.date) 
        else : 
            raise ValidationError(_("Timesheet encoding uom should be either Hours or Days."))

        amount = -timesheet.unit_amount * cost
        #on ne réalise pas de conversion monaitaire car ça n'est pas utile et que ça force une précision à 2 décimales alors que l'on a besoin de 3 décimales

        return amount, cost_line


    def refresh_amount(self):
        _logger.info("---- refresh_amount")
        _logger.info(self.read())
        amount, cost_line = self.compute_amount()
        #_logger.info(str(self.amount) + '_' +str(self.hr_cost_id))
        #_logger.info(str(amount) +'_'+ str(cost_line))
        if "{:.3f}".format(self.amount) != "{:.3f}".format(float_round(amount, precision_digits=3, precision_rounding=None, rounding_method='HALF-UP')) :
            _logger.info("          Change amount of line : before=%s  ===> after =%s" % (self.amount, amount))
            self.amount = amount
        if self.hr_cost_id != cost_line:
            _logger.info("change hr_cost_id > cost line")
            _logger.info(self.hr_cost_id, cost_line)
            self.hr_cost_id =  cost_line
