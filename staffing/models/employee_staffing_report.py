from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

import logging
_logger = logging.getLogger(__name__)

def get_period_begin_date(periodicity, date):
    begin_date = None
    if periodicity == 'week' :
        begin_date = date - relativedelta(days=date.weekday())
    elif periodicity == 'month' :
        begin_date = date.replace(day=1)
    elif periodicity == 'quarter' :
        if date.month < 4:
            quarter_begin_month = 1
        elif date.month < 7:
            quarter_begin_month = 4
        elif date.month < 10:
            quarter_begin_month = 7
        else :
            quarter_begin_month = 10
        begin_date = date.replace(day=1).replace(month=quarter_begin_month)
    elif periodicity == 'semester' :
        if date.month < 7:
            semester_begin_month = 1
        else :
            semester_begin_month = 7
        begin_date = date.replace(day=1).replace(month=semester_begin_month)
    elif periodicity == 'year' :
        begin_date = date.replace(day=1).replace(month=1)
    else :
        raise ValidationError(_("Seule la périodicité hebdomadaire est prise en charge pour le moment."))
    return begin_date

def get_period_end_date(periodicity, period_begin_date):
    end_date = None
    if periodicity == 'week' :
        if period_begin_date.isoweekday() != 1:
            raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité hebdomadaire devrait être un lundi (le premier jour de la semaine en occident)."))
        end_date = period_begin_date + relativedelta(days=6)
    elif periodicity == 'month' :
        if period_begin_date.day != 1:
            raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité mensuelle devrait être le premier jour du mois."))
        end_date = period_begin_date + relativedelta(months=1) - relativedelta(days=1)
    elif periodicity == 'quarter' :
        if period_begin_date.day != 1 or period_begin_date.month not in [1, 4, 7, 10]:
            raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité trimestrielle devrait être le premier jour de janvier, avril, juillet ou octobre."))
        end_date = period_begin_date + relativedelta(months=3) - relativedelta(days=1)
    elif periodicity == 'semester' :
        if period_begin_date.day != 1 or period_begin_date.month not in [1, 7]:
            raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité semestrielle devrait être le premier jour de janvier ou de juillet."))
        end_date = period_begin_date + relativedelta(months=6) - relativedelta(days=1)
    elif periodicity == 'year' :
        if period_begin_date.day != 1 or period_begin_date.month != 1:
            raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité annuelle devrait être le 1er janvier."))
        end_date = period_begin_date + relativedelta(years=1) - relativedelta(days=1)
    else :
        raise ValidationError(_("Seule la périodicité hebdomadaire est prise en charge pour le moment."))
    return end_date


class staffingAnalyticLine_employee_staffing_report(models.Model):
    _inherit = 'account.analytic.line'

    def write(self, vals):
        if not ('unit_amount' in vals.keys () or 'date' in vals.keys() or 'date_end' in vals.keys() or 'employee_id' in vals.keys() or 'category' in vals.keys()):
            return super().write(vals)

        _logger.info('---------- write account.analytic.line employee_staffing_report.py')
        #_logger.info(str(vals))
        for rec in self:
            # Si la date ou l'employee change il faut aussi mettre à jour les rapports de l'ancien employee ou de l'ancienne période qui n'est plus couverte par la nouvelle (pour décrémenter ces "anciens" rapports, et pas seulement créer/mettre à jours les nouveaux)
            if 'date' in vals.keys() or 'date_end' in vals.keys() or 'employee_id' in vals.keys():
                line_end_date = rec.date_end
                if not line_end_date :
                    line_end_date = rec.date
                report_ids = self.env['hr.employee_staffing_report'].search([('employee_id', '=', rec.employee_id.id), ('start_date', '<=', line_end_date), ('end_date', '>=', rec.date)])
                report_ids.sudo().has_to_be_recomputed = True

        res = super().write(vals)

        for rec in self :
            rec.create_update_timesheet_report()

        _logger.info('---------- END write account.analytic.line employee_staffing_report.py')
        return res


    @api.model
    def create(self, vals):
        _logger.info('---------- create account.analytic.line employee_staffing_report.py')
        res = super().create(vals)
        res.create_update_timesheet_report()
        return res

    def unlink(self):
        _logger.info('---------- unlink account.analytic.line employee_staffing_report.py')
        for rec in self:
            if not rec.employee_id :
                continue
            line_end_date = rec.date_end
            if not line_end_date :
                line_end_date = rec.date
            report_ids = self.env['hr.employee_staffing_report'].search([('employee_id', '=', rec.employee_id.id), ('start_date', '<=', line_end_date), ('end_date', '>=', rec.date)])
            report_ids.sudo().has_to_be_recomputed = True

        res = super().unlink()

        if self.env.context.get('do_not_update_staffing_report') != True:
            self.env['hr.employee_staffing_report'].sudo().recompute_if_has_to_be_recomputed()

        return res


    def create_update_timesheet_report(self):
        _logger.info('---------- create_update_timesheet_report account.analytic.line employee_staffing_report.py')
        group_dic = {}
        for line in self :
            if not line.employee_id :
                #_logger.info("Employee_id non defini pour la ligne %s" % str(line.read()))
                continue

            line_end_date = line.date_end
            if not line_end_date :
                line_end_date = line.date

            for periodicity in ['week', 'month', 'quarter', 'semester', 'year']:
                period_begin_date = get_period_begin_date(periodicity, line.date)
                while period_begin_date <= line_end_date:
                    key = periodicity + str(line.employee_id.id) + '_' + str(period_begin_date)
                    if key not in group_dic.keys():
                        group_dic[key] = {
                                'employee_id' : line.employee_id.id,
                                'start_date' : period_begin_date,
                                'periodicity' : periodicity,
                        }
                    period_begin_date = get_period_end_date(periodicity, period_begin_date) + relativedelta(days=1)

        _logger.info("Nombre d'agrégats : %s" % str(len(group_dic.keys())))
        
        for report_dic in group_dic.values():
            #_logger.info(report_dic)
            report = self.env['hr.employee_staffing_report'].search([('employee_id', '=', report_dic['employee_id']), ('periodicity', '=', report_dic['periodicity']), ('start_date', '=', report_dic['start_date'])])
            if len(report):
                report.sudo().has_to_be_recomputed = True
            else :
                self.env['hr.employee_staffing_report'].sudo().create(report_dic)

        if self.env.context.get('do_not_update_staffing_report') != True:
            self.env['hr.employee_staffing_report'].sudo().recompute_if_has_to_be_recomputed()



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
                ], order="date asc")
            _logger.info('Nombre de lignes pointées/previsionnelles : %s' % str(len(lines)))
            lines.with_context(do_not_update_staffing_report=True).create_update_timesheet_report()
        
        self.env['hr.employee_staffing_report'].sudo().recompute_if_has_to_be_recomputed()
        
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
            rec.end_date = get_period_end_date(rec.periodicity, rec.start_date)

    @api.depends('periodicity', 'start_date', 'end_date', 'employee_id')
    def availability(self):
        _logger.info('--- Compute availability Staffing report')
        for rec in self :
            dic = [('employee_id', '=', rec.employee_id.id)]
            pivot_date = datetime.today()

            if (rec.employee_id.first_contract_date and (rec.employee_id.first_contract_date > rec.end_date)) or (rec.employee_id.departure_date and (rec.employee_id.departure_date < rec.start_date)):

                rec.workdays = 0.0
                rec.hollidays = 0.0
                rec.activity_days = 0.0
                rec.project_days = 0.0
                rec.learning_internal_days = 0.0
                rec.sales_internal_days = 0.0
                rec.other_internal_days = 0.0
                rec.activity_days = 0.0
                rec.activity_rate_with_holidays = 0.0
                rec.available_days = 0.0
                rec.activity_previsionnal_project_days = 0.0
                rec.activity_previsionnal_rate = 0.0
                rec.delta_previsionnal_project_days

            else :

                real_start_date = rec.start_date
                if rec.employee_id.first_contract_date and (rec.employee_id.first_contract_date > rec.start_date) :
                    real_start_date = rec.employee_id.first_contract_date
                real_end_date = rec.end_date
                if rec.employee_id.departure_date and (rec.employee_id.departure_date < rec.end_date) :
                    real_end_date = rec.employee_id.departure_date
                
                timesheet_grouped_raw = rec.env['account.analytic.line'].get_timesheet_grouped_raw(pivot_date, date_start=real_start_date, date_end=real_end_date, filters=dic)
                    #On appelle get_timesheet_grouped_raw et non pas get_timesheet_grouped_raw car pour les periodicité mensuelle car on veut borner strictement aux paramètres passés en paramètres
                        #on ne veut pas intégrer les prévisionnels qui ont commencés le lundi 27 novembre pour le rapport du mois de déccembre
                        #... oui mais dans ce cas est-ce qu'il manquera le prédisionnel pour le vendredi 1er décembre ==> normalement non car les périodes prévisionnels sont générées par Napta (SAUF FORÇAGE) par semaine et bout de semaine en cas de semaines à cheval sur deux mois ==> à vérifier #TODO
                lines = timesheet_grouped_raw['aggreation_by_project_type']

                analytic_lines_list_ids = []
                for aggregation in lines.values() :
                    for category in aggregation.values() :
                        for timesheet in category['timesheet_ids']:
                            analytic_lines_list_ids.append(timesheet.id)
                rec.analytic_lines = [(6, 0, analytic_lines_list_ids)]

                #_logger.info(lines)
     
                rec.workdays = rec.employee_id.number_work_days_period(real_start_date, real_end_date) - lines['unavailability']['project_employee_validated']['sum_period_unit_amount']
                rec.hollidays = lines['holidays']['other']['sum_period_unit_amount']
                rec.activity_days = rec.workdays - rec.hollidays
                rec.project_days = lines['mission']['project_employee_validated']['sum_period_unit_amount']
                rec.learning_internal_days = lines['training']['project_employee_validated']['sum_period_unit_amount']
                rec.sales_internal_days = lines['sales']['project_employee_validated']['sum_period_unit_amount']
                rec.other_internal_days = lines['other_internal']['project_employee_validated']['sum_period_unit_amount']
                if rec.activity_days :
                    rec.activity_rate = rec.project_days / rec.activity_days * 100
                else : 
                    rec.activity_rate = None
                if rec.workdays :
                    rec.activity_rate_with_holidays = rec.project_days / rec.workdays * 100
                else :
                    rec.activity_rate_with_holidays = None

                rec.available_days = rec.activity_days - rec.project_days # ce qui est égal à rec.learning_internal_days + rec.sales_internal_days + rec.other_internal_days + LE NON POINTÉ (sur Napta il n'est pas obligé de pointer 100% des jours

                rec.activity_previsionnal_project_days = lines['mission']['project_forecast']['sum_period_unit_amount']
                if rec.activity_days :
                    rec.activity_previsionnal_rate = rec.activity_previsionnal_project_days / rec.activity_days * 100
                else :
                    rec.activity_previsionnal_rate = None
                rec.delta_previsionnal_project_days = rec.activity_previsionnal_project_days - rec.project_days

            if rec.has_to_be_recomputed :
                rec.has_to_be_recomputed = False

    def action_open_analytic_lines(self):
        analytic_lines = self.analytic_lines
        view_id = self.env.ref("staffing.hr_timesheet_line_tree_period_depending")
        return {                                        
                'type': 'ir.actions.act_window',                
                'name': 'Lignes valorisées sur la période du %s au %s' % (self.start_date.strftime("%d/%m/%Y"), self.end_date.strftime("%d/%m/%Y")),
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,          
                'target': 'current',                    
                'domain': [('id', 'in', analytic_lines.ids)],
                'context' : {'no_create' : True, 'period_date_start' : self.start_date, 'period_date_end' : self.end_date, 'search_default_group_category' : True, 'search_default_group_project' : True},
            }


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        #_logger.info('============================================= read_group employee_staffing_report.py')
        #_logger.info(fields)
        #This is a hack to allow us to correctly calculate the average activity rate.

        # fields_name contains only the field names, not the aggregation operator sent after the ':' symbol
        #       The following percentage fields are always aggregated the same way : the aggregation operator sent doesn't matter
        fields_name = []
        for f in fields:
            fields_name.append(f.split(':')[0])

        if 'activity_rate' in fields_name:
            fields.extend(['aggregated_project_days:array_agg(project_days)'])
            fields.extend(['aggregated_activity_days:array_agg(activity_days)'])

        if 'activity_rate_with_holidays' in fields_name:
            fields.extend(['aggregated_project_days2:array_agg(project_days)'])
            fields.extend(['aggregated_workdays:array_agg(workdays)'])
        
        if 'activity_previsionnal_rate' in fields_name :
            fields.extend(['aggregated_activity_previsionnal_project_days:array_agg(activity_previsionnal_project_days)'])
            fields.extend(['aggregated_activity_days2:array_agg(activity_days)'])


        res = []
        if fields:
            res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if 'activity_rate' in fields_name:
            for data in res:
                if data['aggregated_project_days'] and data['aggregated_activity_days']:
                    total_project_days = sum(float(project_days) for project_days in data['aggregated_project_days'] if project_days)
                    total_activity_days = sum(float(activity_days) for activity_days in data['aggregated_activity_days'] if activity_days)
                    data['activity_rate'] = ((total_project_days / total_activity_days) if total_activity_days else 0) * 100
                del data['aggregated_project_days']
                del data['aggregated_activity_days']

        if 'activity_rate_with_holidays' in fields_name:
            for data in res:
                if data['aggregated_project_days2'] and data['aggregated_workdays']:
                    total_project_days = sum(float(project_days) for project_days in data['aggregated_project_days2'] if project_days)
                    total_workdays = sum(float(workdays) for workdays in data['aggregated_workdays'] if workdays)
                    data['activity_rate_with_holidays'] = ((total_project_days / total_workdays) if total_workdays else 0) * 100
                del data['aggregated_project_days2']
                del data['aggregated_workdays']

        if 'activity_previsionnal_rate' in fields_name :
            for data in res:
                if data['aggregated_activity_previsionnal_project_days'] and data['aggregated_activity_days2']:
                    total_activity_previsionnal_project_days = sum(float(activity_previsionnal_project_days) for activity_previsionnal_project_days in data['aggregated_activity_previsionnal_project_days'] if activity_previsionnal_project_days)
                    total_activity_days = sum(float(activity_days) for activity_days in data['aggregated_activity_days2'] if activity_days)
                    data['activity_previsionnal_rate'] = ((total_activity_previsionnal_project_days / total_activity_days) if total_activity_days else 0) * 100
                del data['aggregated_activity_previsionnal_project_days']
                del data['aggregated_activity_days2']

        return res

    def recompute_if_has_to_be_recomputed(self):
        _logger.info('--- recompute_if_has_to_be_recomputed')
        reports = self.env['hr.employee_staffing_report'].search([('has_to_be_recomputed', '=', True)])
        _logger.info('Nombre de rapports de staffing à recalculer : %s' % str(len(reports)))
        _logger.info(reports)
        reports.availability()

    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.job_id')
    def compute_job(self):
        for rec in self:
            rec.rel_job_id = rec.employee_id._get_job_id(rec.start_date)

    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.work_location_id')
    def compute_work_location(self):
        for rec in self:
            rec.rel_work_location_id = rec.employee_id._get_work_location_id(rec.start_date)

    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.department_id')
    def compute_department(self):
        for rec in self:
            rec.rel_department_id = rec.employee_id._get_department_id(rec.start_date)

    @api.depends('employee_id', 'employee_id.contract_ids', 'employee_id.contract_ids.date_start', 'employee_id.contract_ids.date_end', 'employee_id.contract_ids.company_id')
    def compute_company(self):
        for rec in self:
            rec.company_id = rec.employee_id._get_company_id(rec.start_date)

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
    rel_department_id = fields.Many2one('hr.department', compute=compute_department, store=True, help="Département du consultant au début de la période")
    company_id = fields.Many2one('res.company', string='Société', compute=compute_company, store=True, help="Société du consultant")

    start_date = fields.Date('Date de début', required=True)
    end_date = fields.Date('Date de fin', compute=compute_end_date, store=True)
 
    has_to_be_recomputed = fields.Boolean('A recalculer', default=True)
    analytic_lines = fields.Many2many('account.analytic.line', string='Lignes')

    workdays = fields.Float("J. ouvrés", help="nombre de jours ouvrés sur la période qui sont couverts par un contrat de travail.", store=True)
    hollidays = fields.Float("Congés", help="Jours de congés sur la période", store=True)
    activity_days = fields.Float("J. facturables", help="Nombre de jours facturables sur la période = nb jours ouvrés - nb jours congés", store=True)
    learning_internal_days = fields.Float("J. formations", help="Nombre de jours de formation du consultant (et non les actions écoles) sur la période", store=True)
    sales_internal_days = fields.Float("J. avant-vente", help="Nombre de jours avant-vente (experts) sur la période", store=True)
    other_internal_days = fields.Float("J. autres activités internes", help="Nombre de jours autres activités internes sur la période", store=True)
    project_days = fields.Float("J. produits mission", help="Nombre de jours produits en mission sur la période (y compris les missions de la fondation)", store=True)
    activity_rate = fields.Float("TACE", 
            help="Taux d'Activité Congés Exclus sur la période : taux d'activité congés exclus. Somme des jours produits sur mission exclusivement (toutes missions, y compris Fondation) (sans inclure donc avant-vente / formations / etc.), sur les jours réellement disponibles (jours ouvrés moins les jours d'absence de tous types)", 
            store=True, group_operator='avg')
    activity_rate_with_holidays = fields.Float("TACI", 
            help="% TACI = Taux d’Activité Congés Inclus. Somme des jours produits sur mission exclusivement, sur jours ouvrés. Ce n'est pas un indicateur qui montre si on a bien utilisé le temps disponible, mais il permet de se rendre compte du rythme de production (plus faible en période de congés)",
            store=True, group_operator='avg')

    available_days = fields.Float("J. dispo", help="Nombre de jours facturables - nombre de jours pointés en mission exclusivement (toutes missions, y compris Fondation) (sans inclure donc avant-vente / formations / etc.) sur la période", store=True)
    activity_previsionnal_rate = fields.Float("% prévisionnel", help="Taux d'activité prévisionnel sur la période = somme des jours staffés en prévisionnel sur une mission sur les jours réellement disponibles (jours ouvrés moins les jours d'absence de tous types)", store=True, group_operator='avg')
    activity_previsionnal_project_days = fields.Float('Prév. (j)', store=True)
    delta_previsionnal_project_days = fields.Float('Delta prev-pointé (j)', store=True)
