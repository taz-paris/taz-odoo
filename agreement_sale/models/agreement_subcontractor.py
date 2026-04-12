from odoo import models
import logging
_logger = logging.getLogger(__name__)


class AgreementSubcontractorSale(models.Model):
    _inherit = "agreement.subcontractor"

    def get_orders(self):
        self.ensure_one()
        if self.is_partner_id_res_company:
            order_ids = self.env['sale.order'].search([
                ('state', '=', 'sale'),
                ('agreement_id', '=', self.agreement_id.id),
                ('company_id', 'in', [self.sudo().partner_id.ref_company_ids.id]),
            ])
            order_type = 'sale.order'
            _logger.info(order_type)
            _logger.info(order_ids)
            return order_type, order_ids
        return super().get_orders()
