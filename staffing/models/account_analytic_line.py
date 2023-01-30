from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class staffingAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    def write(self, vals):
        if 'staffing_need_id' in vals.keys():
            vals = self._sync_project(vals)
        _logger.info(vals)
        return super().write(vals)

    @api.model
    def create(self, vals):
        #res = []
        #_logger.info(vals)
        #for val in vals:
        #    _logger.info(val)
        #    val = self._sync_project(val)
        #    res.append(val)
        #super().create(res)
        res = self._sync_project(vals)
        return super().create(res)

    def _sync_project(self, vals):
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

    category = fields.Selection(selection_add=[
            ('project_forecast', 'Prévisionnel'), 
            ('project_draft', 'Pointage brouillon'),
            ('project_employee_validated', 'Pointage validé'),
        ])

    staffing_need_id = fields.Many2one('staffing.need', ondelete="restrict")
    hr_cost_id = fields.Many2one('hr.cost', ondelete="restrict")
    employee_job_id = fields.Many2one(string="Grade", related='employee_id.job_id')



    def get_timesheet_grouped(self, pivot_date, date_start=None, date_end=None, filters=None):
        # Usage de cette fonction :
        #   - Calculer le temps pointé / prévisionnel d'un consultant
        #   - Calculer la disponibilité d'un consultant sur une période (passé, présente ou future)
        if date_start and date_end :
            if date_start > date_end :
                raise ValidationError(_("Start date should be <= end date"))

        dic = [('category', '!=', 'project_draft')]

        date_start_substracted_days = 0.0
        if date_start:
            date_start_substracted_days = date_start.weekday()
            date_start_monday = date_start - timedelta(days=date_start_substracted_days)
            dic.append(('date', '>=', date_start_monday))
        date_end_added_days = 0.0
        if date_end :
            date_end_added_days = 6-date_end.weekday()
            date_end_sunday = date_end + timedelta(days=date_end_added_days)
            dic.append(('date', '<', date_end))

        if filters:
            for condition in filters:
                if condition[0] in ['category', 'date']:
                    raise ValidationError(_('Valeur interdite dans le filtre : %s' % condition[0]))
                dic.append(condition)
        timesheets = self.env['account.analytic.line'].search(dic)
        #_logger.info(dic)
        #_logger.info(timesheets)

        previsional_timesheet_ids = []
        validated_timesheet_ids = []
        holiday_timesheet_ids = []

        # Modèle de données :
        #   - La base de données stock des lignes analytic différentes pour le pointage réalisé et le prévisionnel, qui sont conservées en parallèle dans le temps
        #   - Le prévisionnel est exprimé à la semaine : le prévisionnel de la semaine est sur une ligne analytic (voire 2 si cession entre 2 mois au cour de la semaine)
        #   - Le pointé peut être exprimé par jour ou à la semaine
        # Conséquence : la date pivot qui sert à catégoriser et filtrer les lignes doit être exprimée en début de semaine, sinon on risque de compter du prévisionnel ET du pointé pour la même semaine

        #TODO : interdire de modifier le prévisionnel après la fin de la semaine
        #TODO : interdire d'avoir plus d'une ligne d'une catégorie, d'un projet / tesk et d'un employé par date
        #TODO : passer le pointage à validé pour toute la semaine et tous les projets en même temps
           
        #TODO : interdire les affectations hors de la période du projet => ATTENTION : c'est autorisé sur Fitnet donc risque de blocage
                # En revanche : laisser la possibilité de pointer après la date de fin de l'affectation initiale, sinon ça ne sera pas pratique

        monday_pivot_date =  pivot_date - timedelta(days=pivot_date.weekday())
        monday_pivot_date = monday_pivot_date.date()

        for timesheet in timesheets:
            if timesheet.encoding_uom_id != self.env.ref("uom.product_uom_day"):
                continue
            if timesheet.project_id.id == 1147 :
                #ne pas compter les pointage sur "Complément pour soumettre"
                #TODO : pas propre de hardoder l'ID : soit avoir un booléen des lignes à exclure ... soit supprimer ce projet, les staffing.need et les analytics account.line qui vont avec !
                continue
            elif timesheet.project_id.id == 1148 : #Formation dont K4M
                continue
            elif timesheet.project_id.id == 1134 : #23004 TAZ_AVT pour les Experts => ce temps est compté dans leurs objectifs perso mais il ne doit pas être compté comme de l'activité dans Odoo
                continue
            elif timesheet.project_id.id == 1146 : #Autre absence
                if timesheet.category == 'project_employee_validated':
                    if timesheet.date < monday_pivot_date:
                        holiday_timesheet_ids.append(timesheet)
                if timesheet.category == 'project_forecast':
                    if timesheet.date >= monday_pivot_date:
                        holiday_timesheet_ids.append(timesheet)
            elif timesheet.category == 'project_employee_validated':
                if timesheet.date < monday_pivot_date:
                    validated_timesheet_ids.append(timesheet)
            elif timesheet.category == 'project_forecast':
                if timesheet.date >= monday_pivot_date:
                    previsional_timesheet_ids.append(timesheet)
                # Est-ce qu'on garde les prévisionnels antérieurs à la date pivot si rien n'a été pointé ? => NON, on ne bidouille pas : le consultant n'avait qu'à pointer.
                    # => OPTION :  on retourne un indicateur montrant qu'il y a un manque de pointage sur une période antéireure à la date pivot
            elif timesheet.holiday_id:
                holiday_timesheet_ids.append(timesheet)
                # En théorie, le prévisionnel devrait être diminumé des congés par le consultant ou le manager, mais ça peut ne pas être le cas 
                    # => pour une semaine calendaire donnée :
                        # si ***antérieur à monday_pivot*** => alors rien à faire : le pointage validé tient forcément compte des comgés, on ne peut structurellement pas compter 2 fois
                            # ==> ... sauf si la période de congés est enregistrée après la validation du pointage de la semaine considérée ==> le contrôle de jour max de pointage devrait empêcher la validation du congés tant que le pointage validé n'est pas corrigé => vérifier que le message d'erreur lors de la tentative de validation du congés après la vidation du poointage est compréhensible


                        # si ***postérieur ou égal à monday_pivot*** => si la somme congés+previsionnel pour une semaine > nb jours ouvrés de la semaine (aleternative : si (congés+previsionel) > (nb jour pointage max par semaine - nb jours férié sur les jours ouvrés de la semaine) : diminuer le prévisionnel de la différence ==> Bof : pas terrible de faire des choses automatiquement dans le dos du consultant, en plus ça n'est pas pédagogique
                            # ... ou alors on ajoute un contrôle lors de la pose des congés par le salarié (recontrôlé à la validation par Denis) pour que congés+prévisionnel ne dépasse pas nb jour ouvré sur la semaine ===> mais ça ne peut fonctionner que si la demande de congés est gérée dans Odoo => tant qu'on importe de Fitnet il peut y avoir des cas où congés+prévisionel > nb jours ouvrés
                            # TODO une fois la synchro Fitnet terminée : déclencher un wizzard à la validation du congès par le consultant qui lui affiche son prévisionnel et lui demande de l'ajuster

        validated_timesheet_amount = 0.0
        validated_timesheet_unit_amount = 0.0
        for line in validated_timesheet_ids:
            validated_timesheet_amount += line.amount
            validated_timesheet_unit_amount += line.unit_amount

        previsional_timesheet_amount = 0.0
        previsional_timesheet_unit_amount = 0.0
        for line in previsional_timesheet_ids:
            previsional_timesheet_amount += line.amount
            previsional_timesheet_unit_amount += line.unit_amount

        holiday_timesheet_unit_amount = 0.0
        for line in holiday_timesheet_ids:
            holiday_timesheet_unit_amount += line.unit_amount

        res = {
                'monday_pivot_date' : monday_pivot_date,
                'previsional_timesheet_ids' : previsional_timesheet_ids, 
                'validated_timesheet_ids' : validated_timesheet_ids,
                'validated_timesheet_amount' : validated_timesheet_amount,
                'validated_timesheet_unit_amount' : validated_timesheet_unit_amount,
                'previsional_timesheet_amount' : previsional_timesheet_amount,
                'previsional_timesheet_unit_amount' : previsional_timesheet_unit_amount,
                'holiday_timesheet_ids' : holiday_timesheet_ids,
                'holiday_timesheet_unit_amount' : holiday_timesheet_unit_amount,
                }
        #_logger.info(res)
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
        
        self.employee_id.availability()
        #TODO : surcharger unlink pour recalculer l'availability

        if timesheet.holiday_id :
            return False,False

        encoding_uom_id = self.encoding_uom_id
        #self.env.company.timesheet_encode_uom_id
        if encoding_uom_id == self.env.ref("uom.product_uom_hour"):
            cost = timesheet._hourly_cost()
            cost_line = False
        elif encoding_uom_id == self.env.ref("uom.product_uom_day"):
            cost_line = timesheet.employee_id._get_daily_cost(timesheet.date) 
            if not cost_line :
                _logger.info(_("Dayily cost not defined for this employee at this date : %s, %s." % (timesheet.employee_id.name, timesheet.date)))
                return False,False
            cost = cost_line.cost
        else : 
            raise ValidationError(_("Timesheet encoding uom should be either Hours or Days."))

        amount = -timesheet.unit_amount * cost
        amount_converted = timesheet.employee_id.currency_id._convert(
            amount, timesheet.account_id.currency_id or timesheet.currency_id, self.env.company, timesheet.date)

        return amount_converted, cost_line


    def refresh_amount(self):
        #_logger.info("---- refresh_amount")
        amount_converted, cost_line = self.compute_amount()
        if not amount_converted:
            return False
        self.amount = amount_converted
        self.hr_cost_id =  cost_line
