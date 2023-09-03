from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info('---- create analytic.mixin')
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        _logger.info('---- write analytic.mixin')
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def unlink(self):
        _logger.info('---- UNLINK analytic.mixin')
        #TODO : cette fonction n'est pas exécuter lorsque l'on supprime une facture, un SO ou un PO
            # vu que les lignes de ces objets sont supprimées ONCASCADE... cette fonctionne devrait être appelé une fois pour chaque ligne de la facture/SO/PO supprimés !

        old_rel_project_ids = {}
        for rec in self:
            old_rel_project_ids[rec.id] = rec.rel_project_ids
        
        res = super().unlink()

        for project_list_ids in old_rel_project_ids.values():
            for project in project_list_ids:
                project.compute()
        return res
    
    """
    @api.ondelete(at_uninstall=False)
    def _ondelete(self):
        _logger.info('---- @api.ondelete analytic.mixin')
        self._compute_linked_projects()
    """

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
