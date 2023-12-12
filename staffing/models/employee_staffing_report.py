from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

import logging
_logger = logging.getLogger(__name__)


class staffingAnalyticLine_employee_staffing_report(models.Model):
    _inherit = 'account.analytic.line'

    def write(self, vals):
        res = super().write(vals)
        for rec in self :
            rec.create_update_timesheet_report()
            #TODO : si la date ou l'employee change il faut aussi mettre à jour l'ancien rapport pour décrémenter, et pas que le nouveau
        return res


    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.create_update_timesheet_report()
        return res

    def unlink(self):
        report_to_update = []
        for rec in self:
            report_ids = self.env['hr.employee_staffing_report'].search([('employee_id', '=', rec.employee_id.id), ('start_date', '<=', rec.date), ('end_date', '>=', rec.date)])
                #TODO : les critères de dates ne fonctionnent pas si les prévisionnels sont à cheval sur plusieurs semainees/mois
            for report_id in report_ids: #one report by periodicity type (week, month, quarter, semestre, year...)
                report_to_update.append(report_id)

        res = super().unlink()

        for report in report_to_update :
            report.availability()

        return res


    def create_update_timesheet_report(self):
        group_dic = {}
        for line in self :
            if not line.employee_id :
                continue
            #### periodicity = week
            monday = line.date - relativedelta(days=line.date.weekday())
            key = 'week_' + str(line.employee_id.id) + '_' + str(monday)
            if key not in group_dic.keys():
                group_dic[key] = {
                        'employee_id' : line.employee_id.id,
                        'start_date' : monday,
                        'periodicity' : 'week',
                }
            #### periodicity = month
            first_of_month = line.date.replace(day=1)
            key = 'month_' + str(line.employee_id.id) + '_' + str(first_of_month)
            if key not in group_dic.keys():
                group_dic[key] = {
                        'employee_id' : line.employee_id.id,
                        'start_date' : first_of_month,
                        'periodicity' : 'month',
                }
            #### periodicity = quarter
            if line.date.month < 4:
                quarter_begin_month = 1
            elif line.date.month < 7:
                quarter_begin_month = 4
            elif line.date.month < 10:
                quarter_begin_month = 7
            else :
                quarter_begin_month = 10

            first_of_quarter = line.date.replace(day=1).replace(month=quarter_begin_month)
            key = 'quarter_' + str(line.employee_id.id) + '_' + str(first_of_quarter)
            if key not in group_dic.keys():
                group_dic[key] = {
                        'employee_id' : line.employee_id.id,
                        'start_date' : first_of_quarter,
                        'periodicity' : 'quarter',
                }
            #### periodicity = semester
            if line.date.month < 7:
                semester_begin_month = 1
            else :
                semester_begin_month = 7
            first_of_semester = line.date.replace(day=1).replace(month=semester_begin_month)
            key = 'semester_' + str(line.employee_id.id) + '_' + str(first_of_semester)
            if key not in group_dic.keys():
                group_dic[key] = {
                        'employee_id' : line.employee_id.id,
                        'start_date' : first_of_semester,
                        'periodicity' : 'semester',
                }
            #### periodicity = month
            first_of_year = line.date.replace(day=1).replace(month=1)
            key = 'year_' + str(line.employee_id.id) + '_' + str(first_of_year)
            if key not in group_dic.keys():
                group_dic[key] = {
                        'employee_id' : line.employee_id.id,
                        'start_date' : first_of_year,
                        'periodicity' : 'year',
                }

        _logger.info("Nombre d'agrégats : %s" % str(len(group_dic.keys())))

        for report_dic in group_dic.values():
            #_logger.info(report_dic)
            report = self.env['hr.employee_staffing_report'].search([('employee_id', '=', report_dic['employee_id']), ('periodicity', '=', report_dic['periodicity']), ('start_date', '=', report_dic['start_date'])])
            if len(report):
                report[0].sudo().availability()
            else :
                self.env['hr.employee_staffing_report'].sudo().create(report_dic)
 




class HrEmployeeStaffingReport(models.Model):
    _name = "hr.employee_staffing_report"
    _description = "Transient model for employee activity reporting"
    _sql_constraints = [
        ('id_uniq', 'UNIQUE (employee_id, periodicity, start_date)',  "Impossible d'enregistrer deux objets avec le même {employé, périodicité, date de début}.")
    ]


    def reset_all_reports(self):
        _logger.info('HrEmployeeStaffingReport ==> reset_all_reports')
        if len(self) > 0:
            raise ValidationError(_("La réinitialisation des rapports d'activité n'est pas appelable sur un rapport d'activité."))

        self.search([]).sudo().unlink()

        if self.search([], count=True) == 0 :
            lines = self.env['account.analytic.line'].search([
                    #('employee_id', '=', 11), 
                    ('employee_id', '!=', False), 
                    ('project_id', '!=', False), 
                    ('category', 'in', ['project_forecast', 'project_employee_validated', 'other']),
                    ('project_id', '!=', False)
                ], order="date asc")
            _logger.info('Nombre de lignes pointées/previsionnelles : %s' % str(len(lines)))
            lines.create_update_timesheet_report()
            _logger.info('--- END reset_all_reports')


    # s'il on vient de supprimer de la base de donnée la dernière analytic line pour la la période/employé => supprimer le rapport (plutôt que le garder à 0 ?)
    #       Est-ce pertinement sur le plan métier ? Ne vaut-il mieux pas laisser une ligne à 0 ?
    # TODO : tester un cas concret pour vérifier que ça ne bug pas de supprimer l'objet modifié avant de le renvoyer
    """
    def write(self, vals):
        res = super().write(vals)
        for rec in res :
            if len(rec.analytic_lines) == 0:
                res.unlink() 
        return res
    """


    @api.depends('periodicity', 'start_date')
    def compute_end_date(self):
        for rec in self :
            if rec.periodicity == 'week' :
                if rec.start_date.isoweekday() != 1:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité hebdomadaire devrait être un lundi (le premier jour de la semaine en occident)."))
                rec.end_date = rec.start_date + relativedelta(days=6)
            elif rec.periodicity == 'month' :
                if rec.start_date.day != 1:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité mensuelle devrait être le premier jour du mois."))
                rec.end_date = rec.start_date + relativedelta(months=1) - relativedelta(days=1)
            elif rec.periodicity == 'quarter' :
                if rec.start_date.day != 1 or rec.start_date.month not in [1, 4, 7, 10]:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité trimestrielle devrait être le premier jour de janvier, avril, juillet ou octobre."))
                rec.end_date = rec.start_date + relativedelta(months=3) - relativedelta(days=1)
            elif rec.periodicity == 'semester' :
                if rec.start_date.day != 1 or rec.start_date.month not in [1, 7]:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité semestrielle devrait être le premier jour de janvier ou de juillet."))
                rec.end_date = rec.start_date + relativedelta(months=6) - relativedelta(days=1)
            elif rec.periodicity == 'year' :
                if rec.start_date.day != 1 or rec.start_date.month != 1:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité annuelle devrait être le 1er janvier."))
                rec.end_date = rec.start_date + relativedelta(years=1) - relativedelta(days=1)
            else :
                raise ValidationError(_("Seule la périodicité hebdomadaire est prise en charge pour le moment.")) #TODO


    @api.depends('periodicity', 'start_date', 'end_date', 'employee_id')
    def availability(self):
        for rec in self :
            dic = [('employee_id', '=', rec.employee_id.id)]
            pivot_date = datetime.today()

            lines = rec.env['account.analytic.line'].get_timesheet_grouped(pivot_date, date_start=rec.start_date, date_end=rec.end_date, filters=dic)

            analytic_lines_list = lines['previsional_timesheet_ids'] + lines['validated_timesheet_ids'] + lines['holiday_timesheet_ids'] + lines['unavailability_timesheet_ids'] + lines['validated_learning_ids'] + lines['validated_sales_ids'] + lines['validated_other_internal_ids'] + lines['previsional_timesheet_before_pivot_date_ids']
            analytic_lines_list_ids = []
            for l in analytic_lines_list :
                analytic_lines_list_ids.append(l.id)
            rec.analytic_lines = [(6, 0, analytic_lines_list_ids)]


            rec.workdays = rec.employee_id.number_work_days_period(rec.start_date, rec.end_date) - lines['unavailability_unit_amount']
            rec.hollidays = lines['holiday_timesheet_unit_amount']
            rec.activity_days = rec.workdays - rec.hollidays
            rec.project_days = lines['validated_timesheet_unit_amount'] 
            rec.learning_internal_days = lines['validated_learning_unit_amount']
            rec.sales_internal_days = lines['validated_sales_unit_amount']
            rec.other_internal_days = lines['validated_other_internal_unit_amount']
            if rec.activity_days :
                rec.activity_rate = rec.project_days / rec.activity_days * 100
            else : 
                rec.activity_rate = None
            if rec.workdays :
                rec.activity_rate_with_holidays = rec.project_days / rec.workdays * 100
            else :
                rec.activity_rate_with_holidays = None

            rec.available_days = rec.activity_days - rec.project_days # ce qui est égal à rec.learning_internal_days + rec.sales_internal_days + rec.other_internal_days + LE NON POINTÉ (sur Napta il n'est pas obligé de pointer 100% des jours

            rec.activity_previsionnal_project_days = lines['previsional_timesheet_unit_amount'] + lines['previsional_timesheet_before_pivot_date_unit_amount']
            if rec.activity_days :
                rec.activity_previsionnal_rate = rec.activity_previsionnal_project_days / rec.activity_days * 100
            else :
                rec.activity_previsionnal_rate = None
            rec.delta_previsionnal_project_days = rec.activity_previsionnal_project_days - rec.project_days

    def action_open_analytic_lines(self):
        analytic_lines = self.analytic_lines
        view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {                                        
                'type': 'ir.actions.act_window',                
                'name': 'Lignes',
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,          
                'target': 'current',                    
                'domain': [('id', 'in', analytic_lines.ids)],
                'context' : {'search_default_group_category' : True, 'search_default_group_project' : True},
            }


    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        #_logger.info('============================================= read_group employee_staffing_report.py')
        #_logger.info(fields)
        """
        This is a hack to allow us to correctly calculate the average activity rate.
        """
        if 'activity_rate' in fields:
            fields.extend(['aggregated_project_days:array_agg(project_days)'])
            fields.extend(['aggregated_activity_days:array_agg(activity_days)'])

        if 'activity_rate_with_holidays' in fields:
            fields.extend(['aggregated_project_days2:array_agg(project_days)'])
            fields.extend(['aggregated_workdays:array_agg(workdays)'])
        
        if 'activity_previsionnal_rate' in fields :
            fields.extend(['aggregated_activity_previsionnal_project_days:array_agg(activity_previsionnal_project_days)'])
            fields.extend(['aggregated_activity_days2:array_agg(activity_days)'])


        res = []
        if fields:
            res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if 'activity_rate' in fields:
            for data in res:
                if data['aggregated_project_days'] and data['aggregated_activity_days']:
                    total_project_days = sum(float(project_days) for project_days in data['aggregated_project_days'] if project_days)
                    total_activity_days = sum(float(activity_days) for activity_days in data['aggregated_activity_days'] if activity_days)
                    data['activity_rate'] = ((total_project_days / total_activity_days) if total_activity_days else 0) * 100
                del data['aggregated_project_days']
                del data['aggregated_activity_days']

        if 'activity_rate_with_holidays' in fields:
            for data in res:
                if data['aggregated_project_days2'] and data['aggregated_workdays']:
                    total_project_days = sum(float(project_days) for project_days in data['aggregated_project_days2'] if project_days)
                    total_workdays = sum(float(workdays) for workdays in data['aggregated_workdays'] if workdays)
                    data['activity_rate_with_holidays'] = ((total_project_days / total_workdays) if total_workdays else 0) * 100
                del data['aggregated_project_days2']
                del data['aggregated_workdays']

        if 'activity_previsionnal_rate' in fields :
            for data in res:
                if data['aggregated_activity_previsionnal_project_days'] and data['aggregated_activity_days2']:
                    total_activity_previsionnal_project_days = sum(float(activity_previsionnal_project_days) for activity_previsionnal_project_days in data['aggregated_activity_previsionnal_project_days'] if activity_previsionnal_project_days)
                    total_activity_days = sum(float(activity_days) for activity_days in data['aggregated_activity_days2'] if activity_days)
                    data['activity_previsionnal_rate'] = ((total_activity_previsionnal_project_days / total_activity_days) if total_activity_days else 0) * 100
                del data['aggregated_activity_previsionnal_project_days']
                del data['aggregated_activity_days2']

        return res


    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.job_id')
    def compute_job(self):
        for rec in self:
            rec.rel_job_id = rec.employee_id._get_job_id(rec.start_date)

    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.work_location_id')
    def compute_work_location(self):
        for rec in self:
            rec.rel_work_location_id = rec.employee_id._get_work_location_id(rec.start_date)

    periodicity = fields.Selection([
            ('week', 'Semaine'),
            ('month', 'Mois'), #Seules les maillers hebdomadaire et mensuelles sont différentes car elles recouvrent des lignes de pointage différentes. Les périodicités trimestrielles/semestrielles/annuelles pourraient être reconstituées en regroupant sur une liste de mois... mais on aurait pas le bouton pour voir toues les lignes mobilisées à la maille du trimestre/semestre/année (uniquement à la maille des mois)
            ('quarter', 'Trimestre'),
            ('semester', 'Semestre'),
            ('year', 'Année'),
        ], string="Périodicité", default='week')
    employee_id = fields.Many2one('hr.employee', string="Consultant", required=True)
    rel_job_id = fields.Many2one('hr.job', string='Grade', compute=compute_job, store=True, help="Grade du consultant au début de la période")
    rel_work_location_id = fields.Many2one('hr.work.location', compute=compute_work_location, store=True, help="Bureau du consultant au début de la période")

    start_date = fields.Date('Date de début', required=True)
    end_date = fields.Date('Date de fin', compute=compute_end_date, store=True)
 
    analytic_lines = fields.Many2many('account.analytic.line', string='Lignes')

    workdays = fields.Float("J. ouvrés", help="Jours ouvrés sur la période couverts par un contrat de travail.", compute=availability, store=True)
    hollidays = fields.Float("Congés", help="Jours de congés sur la période", compute=availability, store=True)
    activity_days = fields.Float("J. facturables", help="Jours facturables sur la période = nb jours ouvrés - nb jours congés", compute=availability, store=True)
    learning_internal_days = fields.Float("J. formations", help="Jours de formation sur la période", compute=availability, store=True)
    sales_internal_days = fields.Float("J. avant-vente", help="Jours avant-vente (experts) sur la période", compute=availability, store=True)
    other_internal_days = fields.Float("J. autres activités internes", help="Jours autres activités internes sur la période", compute=availability, store=True)
    project_days = fields.Float("J. produits mission", help="Jours produits en mission sur la période (y compris les missions de la fondation)", compute=availability, store=True)
    activity_rate = fields.Float("TACE", 
            help="Taux d'Activité Congés Exclus sur la période : taux d'activité congés exclus. Somme des jours produits sur mission exclusivement (toutes missions, y compris Fondation) (sans inclure donc avant-vente / formations / etc.), sur les jours réellement disponibles (jours ouvrés moins les jours d'absence de tous types)", 
            compute=availability, store=True, group_operator='avg')
    activity_rate_with_holidays = fields.Float("TACI", 
            help="% TACI = Taux d’Activité Congés Inclus. Somme des jours produits sur mission exclusivement, sur jours ouvrés. Ce n'est pas un indicateur qui montre si on a bien utilisé le temps disponible, mais il permet de se rendre compte du rythme de production (plus faible en période de congés)",
            compute=availability, store=True, group_operator='avg')

    available_days = fields.Float("J. dispo", help="Nombre de jours facturables - nombre de jours pointés en mission exclusivement (toutes missions, y compris Fondation) (sans inclure donc avant-vente / formations / etc.) sur la période", compute=availability, store=True)
    activity_previsionnal_rate = fields.Float("% prévisionnel", help="Taux d'activité prévisionnel sur la période = somme des jours staffés en prévisionnel sur une mission sur les jours réellement disponibles (jours ouvrés moins les jours d'absence de tous types)", compute=availability, store=True, group_operator='avg')
    activity_previsionnal_project_days = fields.Float('Prév. (j)', compute=availability, store=True)
    delta_previsionnal_project_days = fields.Float('Delta prev-pointé (j)', compute=availability, store=True)
