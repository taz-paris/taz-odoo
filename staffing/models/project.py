from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class staffingProject(models.Model):
    _inherit = "project.project"

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

    #inspiré de https://github.com/odoo/odoo/blob/fa58938b3e2477f0db22cc31d4f5e6b5024f478b/addons/hr_timesheet/models/hr_timesheet.py#L116
    #@api.depends('project_director_employee_id')
    #def _compute_user_id(self):
    #    for line in self:
    #        line.user_id = line.project_director_employee_id.user_id if line.project_director_employee_id else self._default_user()


    def open_project_pivot_timesheets(self):
        date = datetime.today()
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        rec_ids = timesheets_data['previsional_timesheet_ids'] + timesheets_data['validated_timesheet_ids']

        rec_id = []
        for i in rec_ids:
            rec_id.append(i.id)

        view_id = self.env.ref("staffing.view_project_pivot")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage',
                'res_model': 'account.analytic.line',
                #'res_id': rec_id,
                'view_type': 'pivot',
                'view_mode': 'pivot',
                'view_id': view_id.id,
                'domain' : [('id', 'in', rec_id)],
                'context': {},
                'target': 'current',
            }



    def margin_landing_now(self):
        for rec in self :
            margin_landing_date, margin_text = rec.margin_landing_date(datetime.today())
            rec.margin_landing = margin_landing_date
            rec.margin_text = margin_text

    def margin_landing_date(self, date):
        if not self.order_amount or self.order_amount == 0.0:
            return 0.0
       
        timesheets_data = self.env['account.analytic.line'].get_timesheet_grouped(date, date_start=None, date_end=None, filters=[('project_id', '=', self.id)])
        _logger.info(timesheets_data)
        timesheet_total_amount = timesheets_data['validated_timesheet_amount'] + timesheets_data['previsional_timesheet_amount']

        negative_total_costs = timesheet_total_amount

        margin_landing_date = (self.order_amount + negative_total_costs) / self.order_amount * 100
        #margin_text = "Au %s :\n    - %s jours pointés (%s €)\n   - % jours prévisionnels (%s €)" % (timesheets_data['monday_pivot_date'], timesheets_data['validated_timesheet_unit_amount'], timesheets_data['validated_timesheet_amount'], timesheets_data['previsional_timesheet_unit_amount'], timesheets_data['previsional_timesheet_amount'])
        margin_text = "Projection à terminaison en date du %(monday_pivot_date)s :\n    - %(validated_timesheet_unit_amount).2f jours pointés (%(validated_timesheet_amount).2f €)\n   - %(previsional_timesheet_unit_amount).2f jours prévisionnels (%(previsional_timesheet_amount).2f €)" % timesheets_data
        return margin_landing_date, margin_text

    name = fields.Char(required = False) #Ne peut pas être obligatoire pour la synchro Fitnet
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
