from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectGroup(models.Model):
    _name = 'project.group'
    _description = 'A project group is use for data consolidation purpose'

    def compute(self):
        for rec in self:
            order_amount = 0.0
            billed_amount = 0.0
            payed_amount = 0.0
            group_negative_total_costs = 0.0
            for project in rec.project_ids:
                 if not project.stage_id.is_part_of_booking:
                     continue
                 if project.order_amount :
                     order_amount += project.order_amount
                 if project.billed_amount :
                     billed_amount += project.billed_amount
                 if project.payed_amount :
                     payed_amount += project.payed_amount
                 negative_total_costs, margin_landing_rate, margin_text = project.margin_landing_date(datetime.today())
                 group_negative_total_costs += negative_total_costs
            rec.order_amount = order_amount
            rec.billed_amount = billed_amount
            rec.payed_amount = payed_amount
            rec.negative_total_costs = group_negative_total_costs
            if order_amount == 0:
                rec.margin_landing = False
            else :
                rec.margin_landing = (order_amount + group_negative_total_costs) / order_amount * 100



    #TODO : pour être 100% sur ajouter une contrainte pour vérifier que tous les projets du groupe ont TOUJOURS le client du groupe
    name = fields.Char('Nom', required=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True, domain=[('is_company', '=', True), ('active', '=', True)])
    #TODO pré-remplir le partner_id avec celui du project lorsqu'on crée le project.group à partir du project
    project_ids = fields.One2many('project.project', 'project_group_id', string="Projets")
    description = fields.Html("Description")
    order_amount = fields.Float('Montant commande', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    billed_amount = fields.Float('Montant facturé', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    payed_amount = fields.Float('Montant payé', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    negative_total_costs = fields.Float('Pointage (réal. ou prév.)', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
    margin_landing = fields.Float('Marge à terminaison (%)', compute=compute, help="Seuls les projets dont le statut a le booléen is_part_of_booking vrai sont sommés. Les autres sont ignorés")
