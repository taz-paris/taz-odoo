from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
from datetime import datetime, timedelta
import pytz


import logging
_logger = logging.getLogger(__name__)

class HrEmployeeStaffingReport(models.TransientModel):
    _name = "hr.employee_staffing_report"
    _description = "Transient model for employee activity reporting"
    _sql_constraints = [
        ('id_uniq', 'UNIQUE (employee_id, periodicity, start_date)',  "Impossible d'enregistrer deux objets avec le même {employé, périodicité, date de début}.")
    ]

    #TODO : prendre en compte la quotité de travail dans le nombre de jours dispo (ex si on a un expert à mi-temps)
    #TODO : surcharger la fonction read_group pour calculer ce ration sur les agrégats
    #TODO : Pour les perf passer sur un objet perenne (non transient) et appeler une fonction de MAJ des différents report lorsqu'une ligne analytique évolue
    #TODO : étendre aux agrégats de périodicité mois, trimestre, semestre année


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        _logger.info('HrEmployeeStaffingReport ==> search_read')
        #s'il n'y a aucun enregistrement, on génère les objets de reporting
        if self.search([], count=True) == 0 :
            lines = self.env['account.analytic.line'].search([
                    #('employee_id', '=', 11), 
                    ('project_id', '!=', False), 
                    ('category', 'in', ['project_forecast', 'project_employee_validated', 'other']),
                    ('project_id', '!=', False)
                ], order="date asc")
            _logger.info('Nombre de lignes pointées/previsionnelles : %s' % str(len(lines)))
            group_dic = {}
            for line in lines :
                monday = line.date - timedelta(days=line.date.weekday())
                key = str(line.employee_id.id) + '_' + str(monday)
                if key not in group_dic.keys():
                    group_dic[key] = {
                            'employee_id' : line.employee_id.id,
                            'start_date' : monday,
                            'periodicity' : 'week',
                    }
            _logger.info("Nombre d'agrégats hebdomadaires : %s" % str(len(group_dic.keys())))
            for report_dic in group_dic.values():
                #_logger.info(report_dic)
                self.sudo().create(report_dic)
            _logger.info('--- END search_read')

        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

    @api.depends('periodicity', 'start_date')
    def compute_end_date(self):
        for rec in self :
            if rec.periodicity == 'week' :
                if rec.start_date.isoweekday() != 1:
                    raise ValidationError(_("La date de début d'un rapport d'activité avec une périodicité hebdomadaire devrait être un lundi"))
                rec.end_date = rec.start_date + timedelta(days=6)
            else :
                raise ValidationError(_("Seule la périodicité hebdomadaire est prise en charge pour le moment.")) #TODO


    @api.depends('periodicity', 'start_date', 'end_date', 'employee_id')
    def availability(self):
        for rec in self :
            dic = [('employee_id', '=', rec.employee_id.id)]
            pivot_date = datetime.today()

            lines = rec.env['account.analytic.line'].get_timesheet_grouped(pivot_date, date_start=rec.start_date, date_end=rec.end_date, filters=dic)

            analytic_lines_list = lines['previsional_timesheet_ids'] + lines['validated_timesheet_ids'] + lines['holiday_timesheet_ids']
            analytic_lines_list_ids = []
            for l in analytic_lines_list :
                analytic_lines_list_ids.append(l.id)
            rec.analytic_lines = [(6, 0, analytic_lines_list_ids)]

            work_days_period = rec.employee_id.number_work_days_period(rec.start_date, rec.end_date)

            rec.hollidays = lines['holiday_timesheet_unit_amount']
            rec.workdays = work_days_period
            rec.activity_days = work_days_period - rec.hollidays
            rec.project_days = lines['validated_timesheet_unit_amount'] 
            rec.learning_internal_days = rec.activity_days - rec.project_days
            if rec.activity_days :
                rec.activity_rate = rec.project_days / rec.activity_days * 100
            else : 
                rec.activity_rate = None
            if rec.workdays :
                rec.activity_rate_with_holidays = rec.project_days / rec.workdays * 100
            else :
                rec.activity_rate_with_holidays = None

            rec.available_days = rec.employee_id.number_days_available_period(rec.start_date, rec.end_date)

            rec.activity_previsionnal_project_days = lines['previsional_timesheet_unit_amount']
            rec.delta_previsionnal_project_days = rec.activity_previsionnal_project_days - rec.project_days
            if rec.activity_days :
                rec.activity_previsionnal_rate = lines['previsional_timesheet_unit_amount'] / rec.activity_days * 100
            else :
                rec.activity_previsionnal_rate = None

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


    periodicity = fields.Selection([
            ('week', 'Semaine'),
            #('month', 'Mois'),
            #('quarter', 'Trimestre'),
            #('semester', 'Semestre'),
            #('year', 'Année'),
        ], string="Périodicité", default='week')
    employee_id = fields.Many2one('hr.employee', string="Consultant")
    rel_job_id = fields.Many2one(related='employee_id.job_id', store=True)

    start_date = fields.Date('Date de début')
    end_date = fields.Date('Date de fin', compute=compute_end_date, store=True)
 
    analytic_lines = fields.Many2many('account.analytic.line', string='Lignes')

    workdays = fields.Float("J. ouvrés", help="Jours ouvrés sur la période couverts par un contrat de travail.", compute=availability, store=True)
    hollidays = fields.Float("Congés", help="Jours de congés sur la période", compute=availability, store=True)
    activity_days = fields.Float("J. facturables", help="Jours facturables sur la période = nb jours ouvrés - nb jours congés", compute=availability, store=True)
    learning_internal_days = fields.Float("J. internes+fomations", help="Jours internes + formation sur la période", compute=availability, store=True)
    project_days = fields.Float("J. produits mission", help="Jours produits en mission sur la période (y compris les missions de la fondation)", compute=availability, store=True)
    activity_rate = fields.Float("TACE", 
            help="Taux d'Activité Congés Exclus sur la période : taux d'activité congés exclus. Somme des jours produits sur mission exclusivement (toutes missions, y compris Fondation) (sans inclure donc avant-vente / formations / etc.), sur les jours réellement disponibles (jours ouvrés moins les jours d'absence de tous types)", 
            compute=availability, store=True, group_operator=False) #TODO : surcharger la fonction read_group pour calculer ce ration sur les agrégats
    activity_rate_with_holidays = fields.Float("TACI", 
            help="% TACI = Taux d’Activité Congés Inclus. Somme des jours produits sur mission exclusivement, sur jours ouvrés. Ce n'est pas un indicateur qui montre si on a bien utilisé le temps disponible, mais il permet de se rendre compte du rythme de production (plus faible en période de congés)",
            compute=availability, store=True, group_operator=False) #TODO : surcharger la fonction read_group pour calculer ce ration sur les agrégats

    available_days = fields.Float("J. dispo", help="Nombre de jours disponibles sur la période", compute=availability, store=True)
    activity_previsionnal_rate = fields.Float("% prévisionnel", help="Taux d'activité prévisionnel sur la période", compute=availability, store=True, group_operator=False) #TODO : surcharger la fonction read_group pour calculer ce ration sur les agrégats
    activity_previsionnal_project_days = fields.Float('Prév. (j)', compute=availability, store=True)
    delta_previsionnal_project_days = fields.Float('Delta prev-pointé (j)', compute=availability, store=True)
