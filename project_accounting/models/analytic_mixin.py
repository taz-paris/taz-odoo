from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def _compute_linked_projects(self):
        for rec in self:
            for project in rec.rel_project_ids:
                project.compute()


    @api.depends('analytic_distribution')
    def comptute_project_ids(self):
        for rec in self:
            project_ids_res = []
            #for analytic_account in self.env['account.analytic.account'].browse(rec.analytic_distribution.keys()):
            if rec.analytic_distribution:
                for analytic_account_id in rec.analytic_distribution.keys():
                    analytic_account = self.env['account.analytic.account'].search([('id', '=', analytic_account_id)])[0]
                    if len(analytic_account.project_ids):
                        for project_id in analytic_account.project_ids:
                            project_ids_res.append(project_id.id)

            if len(project_ids_res):
                rec.rel_project_ids = [(6, 0, project_ids_res)] 
            else :
                rec.rel_project_ids = False
   

    rel_project_ids = fields.Many2many('project.project', string="Projets", compute=comptute_project_ids)
