from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectProject(models.Model):
    _inherit = "project.project"
   
    def compute_is_related_to_miror_project(self):
        for rec in self :
            is_related_to_miror_project = False
            if len(rec.mirored_project_outsourcing_link_ids) != 0 :
                is_related_to_miror_project = True
            for project_outsourcing_link_id in rec.project_outsourcing_link_ids:
                if project_outsourcing_link_id.inter_company_mirror_project :
                    is_related_to_miror_project = True
            rec.is_related_to_miror_project = is_related_to_miror_project


    is_related_to_miror_project = fields.Boolean(compute = compute_is_related_to_miror_project)
    mirored_project_outsourcing_link_ids = fields.One2many('project.outsourcing.link', 
                                                            'inter_company_mirror_project', 
                                                            check_company=False,
                                                            string="Liens projet-fourniseur des projets 'clients'") 
