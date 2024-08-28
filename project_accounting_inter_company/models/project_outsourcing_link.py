from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectOutsourcingLink(models.Model):
    _inherit = "project.outsourcing.link"

    inter_company_mirror_project = fields.Many2one('project.project', 'Projet miroir')

    def get_or_generate_inter_company_mirror_project(self) :
        _logger.info('==== get_or_generate_inter_company_mirror_project')
        self.ensure_one()
        if self.inter_company_mirror_project:
            return self.inter_company_mirror_project
        if len(self.partner_id.ref_company_ids) != 1:
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
