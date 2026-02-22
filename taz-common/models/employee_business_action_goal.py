from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

import datetime

class employeeBusinessActionGoal(models.Model):
    _name = "taz.employee_business_action_goal"
    _description = "Employee Business Action Goal"
    _order = "reference_period desc"
    _sql_constraints = [
        ('user_year_type_uniq', 'UNIQUE (user_id, reference_period, type)', 
         "Impossible d'avoir deux objectifs pour le même utilisateur, la même année et le même type d'action.")
    ]

    @api.model
    def year_selection(self):
        year = 2024
        year_list = []
        while year != datetime.date.today().year + 2:
            year_list.append((str(year), str(year)))
            year += 1
        return year_list

    @api.model
    def year_default(self):
        return str(datetime.date.today().year)

    @api.depends('user_id', 'reference_period', 'type')
    def _compute_name(self):
        for rec in self:
            type_label = dict(self._fields['type'].selection).get(rec.type, "")
            rec.name = "%s - %s - %s" % (rec.reference_period or "", rec.user_id.name or "", type_label)

    def _get_period_action(self):
        self.ensure_one()
        start_date = datetime.date(int(self.reference_period), 1, 1)
        end_date = datetime.date(int(self.reference_period), 12, 31)
            
        domain = [
            ('date_deadline', '>=', start_date),
            ('date_deadline', '<=', end_date),
            ('action_type', '=', self.type),
            ('user_ids', 'in', [self.user_id.id]),
            ('state', '=', 'done')
        ]
        action_list = self.env['taz.business_action'].search(domain)
        period_action_count = len(action_list)
        return action_list, period_action_count

    def compute(self):
        for rec in self:
            if not rec.user_id or not rec.reference_period or not rec.type:
                rec.period_action_count = 0
                rec.period_rate = 0
                continue
            
            action_list, rec.period_action_count = rec._get_period_action()
            
            if rec.period_goal > 0:
                rec.period_rate = (rec.period_action_count / rec.period_goal) * 100.0
            else:
                rec.period_rate = 0.0

    def action_view_details(self):
        self.ensure_one()
        action_list, period_action_count = self._get_period_action()
        domain = [('id', 'in', action_list.ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Détail des actions de %s pour l\'année %s' % (self.user_id.name, self.reference_period)),
            'res_model': 'taz.business_action',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': domain,
            'context': {'create': False},
        }

    user_id = fields.Many2one('res.users', string="Utilisateur", required=True, ondelete='restrict')
    reference_period = fields.Selection(year_selection, string="Année", default=year_default, required=True)
    type = fields.Selection([
        ('regular_news', 'RDV Intimité réseau'),
        ('commercial_interview', 'RDV commercial avec DM / en délégation'),
        ('propale', 'Contribution à une proposition commerciale'),
        ('first_meeting', 'RDV Prise de connaissance/Découverte'),
        ('deepening', 'RDV Approfondissement'),
        ('other', 'Autre action commerciale (non RDV)'),
    ], string="Type d'action", required=True)
    
    period_goal = fields.Integer("Objectif annuel")
    period_action_count = fields.Integer("Réalisé à date", compute='compute')
    period_rate = fields.Float("Ratio atteint/objectif (%)", compute='compute')
    
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    name = fields.Char("Libellé", compute='_compute_name', store=True)
    note = fields.Text("Commentaire")
