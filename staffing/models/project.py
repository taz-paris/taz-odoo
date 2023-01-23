from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class staffingProjectStage(models.Model):
    _inherit = "project.project.stage"

    is_part_of_booking = fields.Boolean('Compte dans le book', help="Les projects qui sont à cette étape comptent dans le book.")

class projectGroup(models.Model):
    _name = 'project.group'
    _description = 'A project group is use for data consolidation purpose'

    def compute(self):
        for rec in self:
            order_amount = 0.0
            billed_amount = 0.0
            payed_amount = 0.0
            group_negative_total_costs = 0.0
            for project in rec.project_ids:
                 if not project.stage_id.is_part_of_booking:
                     continue
                 if project.order_amount :
                     order_amount += project.order_amount
                 if project.billed_amount :
                     billed_amount += project.billed_amount
                 if project.payed_amount :
                     payed_amount += project.payed_amount
                 negative_total_costs, margin_landing_rate, margin_text = project.margin_landing_date(datetime.today())
                 group_negative_total_costs += negative_total_costs
            rec.order_amount = order_amount
            rec.billed_amount = billed_amount
            rec.payed_amount = payed_amount
            rec.negative_total_costs = group_negative_total_costs
            if order_amount == 0:
                rec.margin_landing = False
            else :
                rec.margin_landing = (order_amount + group_negative_total_costs) / order_amount * 100



    #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    name = fields.Char('Nom', required=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True, domain=[('is_company', '=', True), ('active', '=', True)])
    #TODO pré-remplir le partner_id avec celui du project lorsqu'on crée le project.group à partir du project
    project_ids = fields.One2many('project.project', 'project_group_id', string="Projets")
    description = fields.Html("Description")
    order_amount = fields.Float('Montant commande', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    billed_amount = fields.Float('Montant facturé', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    payed_amount = fields.Float('Montant payé', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    negative_total_costs = fields.Float('Pointage (réal. ou prév.)', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    margin_landing = fields.Float('Marge à terminaison (%)', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")


class timesheetNavigator(models.TransientModel):
    _name = 'timesheet.navigator'
    _description = "Technical object for storing navigation session data."

    user_id = fields.Many2one('res.users', string="Who looks") 
    employee_id = fields.Many2one('hr.employee', string="Consultant")
    begin_date = fields.Date("Semaine du")

    def open_timesheet_navigator(self):
        navigators = self.env['timesheet.navigator'].search([('user_id', '=', self.env.user.id)])
        if len(navigators) == 1:
            rec = navigators[0]
        else :
            d = datetime.today()
            new_current_monday = d - timedelta(days=d.weekday())
            new_current_monday = new_current_monday.date()
            employ = self.env.user.employee_id
            if employ :
                rec = self.env['timesheet.navigator'].create({'user_id' : self.env.user.id, 'begin_date' : new_current_monday, 'employee_id': employ.id})
        return {                
                'type': 'ir.actions.act_window',
                'name': 'Sélection de la semaine et du consultant',
                'res_model': 'timesheet.navigator',
                'res_id': rec.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

    def validate(self):
        return self.env['project.project'].open_timesheet_navigate_weeks('no-change', target='main')


class staffingProject(models.Model):
    _inherit = "project.project"
    _order = "number desc"

    #@api.model
    #def create(self, vals):
    #    if vals.get('number', '') == '':
    #            vals['number'] = self.env['ir.sequence'].next_by_code('project.project') or ''
    #    res = super().create(vals)
    #    return res

    def name_get(self):
        res = []
        for rec in self:
            display_name = "%s %s (%s)" % (rec.number or "", rec.name or "", rec.partner_id.name or "")
            res.append((rec.id, display_name))
        return res

    def name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|', '|', ('number', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    #inspiré de https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_timesheet/models/hr_timesheet.py#L116
    @api.depends('project_director_employee_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.project_director_employee_id.user_id if rec.project_director_employee_id else False


    def open_project_pivot_timesheets(self):
        date = datetime.today()
        rec_id = []

        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids']

        for i in rec_ids:
            rec_id.append(i.id)

        pivot_view_id = self.env.ref("staffing.view_project_pivot")
        tree_view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot,tree',
                'view_id': [pivot_view_id.id, tree_view_id.id],
                'domain' : [('id', 'in', rec_id)],
                'context': {},
                'target': 'current',
            }


    def open_forecast_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=date+timedelta(days=-21), date_end=date+timedelta(days=90), filters=[])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids'] + timesheets_data['holiday_timesheet_ids']

        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)

        view_id = self.env.ref("staffing.view_forecast_pivot")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Forecast',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', rec_id)],
                'context': {'pivot_measures': ['unit_amount']},
                'target': 'current',
            }





    def open_timesheet_navigate_weeks(self, sens, target='current'):
        _logger.info('--open_timesheet_navigate_weeks')
        view_id = self.env.ref("staffing.view_timesheets_tree")
        #Impossible to send context to a server action from a menuItem, so we use a dédicated transient model
        # TODO : LIMITS : if the user has 2 web browser tabs opened, the navigation will have conflicts 
        navigators = self.env['timesheet.navigator'].search([('user_id', '=', self.env.user.id)])
        if len(navigators) == 1:
            navigator = navigators[0]
            bd = navigator.begin_date 
            timesheet_current_monday = bd - timedelta(days=bd.weekday())
            if sens == 'next':
                new_current_monday = timesheet_current_monday + timedelta(days=7)
            elif sens == 'previous' :
                new_current_monday = timesheet_current_monday - timedelta(days=7)
            elif sens == 'no-change' :
                new_current_monday = timesheet_current_monday
            employ = navigator.employee_id
            navigator.begin_date = new_current_monday
        else :
            d = datetime.today()
            new_current_monday = d - timedelta(days=d.weekday())
            new_current_monday = new_current_monday.date()
            employ = self.env.user.employee_id
            if employ :
                self.env['timesheet.navigator'].create({'user_id' : self.env.user.id, 'begin_date' : new_current_monday, 'employee_id': employ.id})

        sunday = new_current_monday + timedelta(days=6)

        #TODO : créer à la volée les lignes de prévisionel/pointage manquante (pour tous les staffing qui ont une date début < sunday et une date de fin > monday)
            # ça permettra d'être ceinture et bretelle, notamment pour les lignes de projets interne, formation etc.

        #TODO : si employ == False : ouvrir le wizzard de sélection de l'emplpoyee/date
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=new_current_monday, date_end=sunday, filters=[('employee_id', '=', employ.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids'] + timesheets_data['holiday_timesheet_ids']
        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)
        domain = [('date', '>=', new_current_monday), ('date', '<=', sunday), ('id', 'in', rec_id)]

        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage semaine du %s au %s de %s %s ' % (new_current_monday.strftime('%d/%m/%Y'), str(sunday.strftime('%d/%m/%Y')), employ.first_name or ' ', employ.name or ''),
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'domain' : domain,
                'target': target,
                'context' : {'employee_id' : employ.id},
            }

    def margin_landing_now(self):
        for rec in self :
            negative_total_costs, margin_landing_rate, margin_text = rec.margin_landing_date(datetime.today())
            rec.margin_landing = margin_landing_rate
            rec.margin_text = margin_text

    def margin_landing_date(self, date):
        if not self.order_amount or self.order_amount == 0.0:
            return 0.0, 0.0, ""
       
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        _logger.info(timesheets_data)
        timesheet_total_amount = timesheets_data['validated_timesheet_amount'] + timesheets_data['previsional_timesheet_amount']

        #partner_id = fields.Many2one(required=True, ondelete="restrict")
        negative_total_costs = timesheet_total_amount
        date = fields.Date(string="Date de fin")

        margin_landing_rate = (self.order_amount + negative_total_costs) / self.order_amount * 100
        margin_text = "Projection à terminaison en date du %(monday_pivot_date)s :\n    - %(validated_timesheet_unit_amount).2f jours pointés (%(validated_timesheet_amount).2f €)\n    - %(previsional_timesheet_unit_amount).2f jours prévisionnels (%(previsional_timesheet_amount).2f €)" % timesheets_data
        return negative_total_costs, margin_landing_rate, margin_text


    def write(self, vals):
        if 'stage_id' in vals.keys():
            vals['state_last_change_date'] = datetime.today()
        return super().write(vals)

    @api.model
    def create(self, vals):
        vals['state_last_change_date'] = datetime.today()
        return super().create(vals)
    
    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
    project_group_id = fields.Many2one('project.group', string='Groupe de projets', domain="[('partner_id', '=', partner_id)]")
        #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    favorite_user_ids = fields.Many2many(string="Intéressés par ce projet")
    stage_is_part_of_booking = fields.Boolean(related="stage_id.is_part_of_booking")
    partner_id = fields.Many2one(domain="[('is_company', '=', True)]")
    project_director_employee_id = fields.Many2one('hr.employee', "Directeur de mission", default=lambda self: self.env.user.employee_id) #TODO : synchroniser cette valeur avec user_id avec un oneChange
    staffing_need_ids = fields.One2many('staffing.need', 'project_id')
    probability = fields.Selection([
            ('0', '0 %'),
            ('30', '30 %'),
            ('70', '70 %'),
            ('100', '100 %'),
        ], string='Probabilité')
    order_amount = fields.Float('Montant commande')
    billed_amount = fields.Float('Montant facturé', readonly=True)
    payed_amount = fields.Float('Montant payé', readonly=True)
    margin_target = fields.Float('Objectif de marge (%)') #TODO : contrôler que c'est positif et <= 100
    margin_landing = fields.Float('Marge à terminaison (%)', compute=margin_landing_now)
    margin_text = fields.Text('Détail de la marge', compute=margin_landing_now)
    state_last_change_date = fields.Date('Date de dernier changement de statut', help="Utilisé pour le filtre Nouveautés de la semaine")

    number = fields.Char('Numéro', readonly=True, required=True, copy=False, default='New')
    is_purchase_order_received = fields.Boolean('Bon de commande reçu')
    purchase_order_number = fields.Char('Numéro du bon de commande')
    remark = fields.Text("Remarques")
    outsourcing = fields.Selection([
            ('no-outsourcing', 'Sans sous-traitance'),
            ('co-sourcing', 'Avec Co-traitance'),
            ('direct-paiement-outsourcing', 'Sous-traitance paiement direct'),
            ('direct-paiement-outsourcing-company', 'Sous-traitance paiement direct + Tasmane'),
            ('outsourcing', 'Sous-traitance paiement Tasmane'),
        ], string="Type de sous-traitance")
    #TODO : ajouter un type (notamment pour les accords cadre) ? ou bien utiliser les tags ?
    #TODO : ajouter les personnes intéressées pour bosser sur le projet
    #TODO : ajouter les personnes qui ont travaillé sur la propale + double book
    #TODO : ajouter un sur-objet "group project"
