from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectProject(models.Model):
    _inherit = "project.project"
    
    mirored_project_outsourcing_link_ids = fields.One2many('project.outsourcing.link', 
                                                            'inter_company_mirror_project', 
                                                            check_company=False,
                                                            string="Liens projet-fourniseur des projets 'clients'") 
