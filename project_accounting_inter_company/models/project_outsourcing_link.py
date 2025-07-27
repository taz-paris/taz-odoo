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
            dest_company = (
                    rec.sudo().partner_id.commercial_partner_id.ref_company_ids
            )
            if dest_company and dest_company.so_from_po:
                rec.is_partner_id_res_company = True
            else :
                rec.is_partner_id_res_company = False

    is_partner_id_res_company = fields.Boolean(compute="_compute_is_partner_id_res_company")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.is_partner_id_res_company:
                record.get_or_generate_inter_company_mirror_project()
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self :
            if rec.is_partner_id_res_company and not(rec.inter_company_mirror_project) :
                rec.get_or_generate_inter_company_mirror_project()
        return res

    def get_or_generate_inter_company_mirror_project(self) :
        _logger.info('==== get_or_generate_inter_company_mirror_project')
        self.ensure_one()
        if self.inter_company_mirror_project:
            return self.inter_company_mirror_project

        if not self.is_partner_id_res_company :
            raise ValidationError(_("Le partenaire lié n'est pas lié à une société de la galaxie."))
        
        partner_secondary_ids  = []
        if self.project_id.partner_id.id != self.company_id.partner_id.id :
            partner_secondary_ids.append((4, self.company_id.partner_id.id))

        dest_company = self.partner_id.ref_company_ids[0].id

        dic_mirror_project = {
            'name' : self.project_id.name,
            'company_id' : dest_company,
            'partner_id' : self.project_id.partner_id.id,
            'stage_id' : self.project_id.stage_id.id,
            'outsourcing' : False,
            'agreement_id' : False,
            'project_director_employee_id' : self.project_id.project_director_employee_id.id,
            'project_manager' : self.project_id.project_manager.id,
            'partner_secondary_ids' : partner_secondary_ids,
            'is_prevent_napta_creation' : self.project_id.is_prevent_napta_creation,
            'date_win_loose' : self.project_id.date_win_loose,
            }
        _logger.info(dic_mirror_project)
        self.inter_company_mirror_project = self.env['project.project'].with_company(dest_company).with_context(allow_all_status=True).create(dic_mirror_project)

        return self.inter_company_mirror_project
