from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)


class AgreementSubcontractor(models.Model):
    _inherit = "agreement.subcontractor"

    def get_orders(self):
        self.ensure_one()
        if not self.is_partner_id_res_company:
            order_ids = self.env['purchase.order'].search([
                ('state', '=', 'purchase'),
                ('agreement_id', '=', self.agreement_id.id),
                ('partner_id', 'in', [self.partner_id.id]),
                #TODO : il faudrait également regarder tous les partner_id de la descendance du partner_id du DC4
            ])
            order_type = 'purchase.order'
            _logger.info(order_type)
            _logger.info(order_ids)
            return order_type, order_ids
        return super().get_orders()
