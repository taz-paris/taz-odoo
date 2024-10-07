from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectOutsourcingLink(models.Model):
    _inherit = "project.outsourcing.link"

    inter_company_mirror_project = fields.Many2one('project.project', 'Projet miroir', check_company=False, help="Le projet miroir est créé automatiquement lors de la validation du premier BCF ou de la première facture.\n S'il existe déjà projet miroir dans le référentiel des projets de la filiale fournisseuse, il est possible de le renseigner à la main.")

    @api.depends('partner_id', 'partner_id.ref_company_ids')
    def _compute_is_partner_id_res_company(self):
        for rec in self:
            if len(rec.partner_id.ref_company_ids) != 1:
                rec.is_partner_id_res_company = False
            else :
                rec.is_partner_id_res_company = True

    is_partner_id_res_company = fields.Boolean(compute="_compute_is_partner_id_res_company")

    def get_or_generate_inter_company_mirror_project(self) :
        _logger.info('==== get_or_generate_inter_company_mirror_project')
        self.ensure_one()
        if self.inter_company_mirror_project:
            return self.inter_company_mirror_project
        if not self.is_partner_id_res_company :
            raise ValidationError(_("Le partenaire lié n'est pas lié à une société de la galaxie."))
        
        dic_mirror_project = {
            'name' : self.project_id.name,
            'company_id' : self.partner_id.ref_company_ids[0].id,
            'partner_id' : self.project_id.partner_id.id,
            'stage_id' : self.project_id.stage_id.id,
            'outsourcing' : False,
            'agreement_id' : False,
            'project_director_employee_id' : self.project_id.project_director_employee_id.id,
            'project_manager' : self.project_id.project_manager.id,
            'partner_secondary_ids' : [(4, self.company_id.partner_id.id)],
            }
        _logger.info(dic_mirror_project)
        self.inter_company_mirror_project = self.env['project.project'].with_context(allow_all_status=True).create(dic_mirror_project)

        return self.inter_company_mirror_project
