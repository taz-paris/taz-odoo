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
        self.ensure_one()
        if self.inter_company_mirror_project:
            return self.inter_company_mirror_project
        if not self.partner_id.company_id:
            raise ValidationError(_("Le partenaire lié n'est pas lié à une société de la galaxie."))
        
        self.inter_company_mirror_project = self.env['project.project'].create({
            'company_id' : self.partner_id.company_id.id,
            'partner_id' : self.project_id.partner_id.id,
            'stage_id' : self.project_id.stage_id,
            'outsourcing' : False,
            'agreement_id' : False,
            'project_director_employee_id' : self.project_id.project_director_employee_id.id,
            'project_manager' : self.project_id.project_manager.id,
            'partner_secondary_id' : [(4, self.partner_id.id)],
            })

        return self.inter_company_mirror_project
