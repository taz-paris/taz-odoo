from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    

    def get_dest_analytic_distribution(self, analytic_distribution, dest_company, origin_company):
        _logger.info('=================  get_dest_analytic_distribution')
        dest_analytic_distribution = {}
        
        if analytic_distribution:
            for analytic_account_id, rate in analytic_distribution.items() :
                analytic_account_id = self.env['account.analytic.account'].browse([int(analytic_account_id)])

                if analytic_account_id.project_count != 1:
                    raise ValidationError(_("Ce compte analytique ne peut pas être traité automatiquement car il n'est pas lié à exactement un projet."))
                project_id = analytic_account_id.project_ids[0] 
                project_outsourcing_link_ids = self.env['project.outsourcing.link'].search([('company_id', '=', origin_company.id), ('project_id', '=', project_id.id), ('partner_id', '=', dest_company.partner_id.id)])
                if len(project_outsourcing_link_ids) != 1:
                    raise ValidationError(_("Le projet %s n'a pas de lien projet/sous-traitant avec la société %s" % (project_id.display_name, dest_company.partner_id.display_name)))
                project_outsourcing_link_id = project_outsourcing_link_ids[0]
                dest_project = project_outsourcing_link_id.get_or_generate_inter_company_mirror_project()
                dest_analytic_distribution[str(dest_project.analytic_account_id.id)] = rate

        return dest_analytic_distribution



    def get_dest_analytic_distribution_from_supplier_company(self, analytic_distribution, dest_company, origin_company):
        _logger.info('=================  get_dest_analytic_distribution_from_supplier_company')
        dest_analytic_distribution = {}
        
        if analytic_distribution:
            for analytic_account_id, rate in analytic_distribution.items() :
                analytic_account_id = self.env['account.analytic.account'].browse([int(analytic_account_id)])

                if analytic_account_id.project_count != 1:
                    raise ValidationError(_("Ce compte analytique ne peut pas être traité automatiquement car il n'est pas lié à exactement un projet."))
                project_id = analytic_account_id.project_ids[0]

                project_outsourcing_link_ids = self.env['project.outsourcing.link'].search([('inter_company_mirror_project', '=', project_id.id), ('company_id', '=', dest_company.id), ('partner_id', '=', origin_company.partner_id.id)])
                if len(project_outsourcing_link_ids) != 1:
                    raise ValidationError(_("Le projet %s n'a pas de lien projet/sous-traitant avec la société %s" % (project_id.display_name, dest_company.partner_id.display_name)))
                project_outsourcing_link_id = project_outsourcing_link_ids[0]
                dest_project = project_outsourcing_link_id.project_id
                dest_analytic_distribution[str(dest_project.analytic_account_id.id)] = rate

        return dest_analytic_distribution

    def _inter_company_create_sale_order(self, dest_company):
        # To avoid creating multiple sale orders for the same purchase order on sale order confirmation
        self.ensure_one()
        if not(self.intercompany_sale_order_id):
            return super()._inter_company_create_sale_order(dest_company)

    def _prepare_sale_order_line_data(self, purchase_line, dest_company, sale_order):
        new_line = super()._prepare_sale_order_line_data(purchase_line, dest_company, sale_order)
        new_line['analytic_distribution'] = self.get_dest_analytic_distribution(purchase_line.analytic_distribution, dest_company, purchase_line.company_id)
        new_line['previsional_invoice_date'] = purchase_line['previsional_invoice_date']
        new_line['price_unit'] = purchase_line['price_unit']
        new_line['name'] = purchase_line['name']
        return new_line



class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    def _get_purchase_sale_line_sync_fields(self):
        #_logger.info('---- override _get_purchase_sale_line_sync_fields')
        res = super()._get_purchase_sale_line_sync_fields()
        res['name'] = 'name' 
        res['product_id'] = 'product_id' 
        res['product_uom'] = 'product_uom' 
        res['qty_received'] = 'qty_delivered' 
        res['price_unit'] = 'price_unit' 
        res['previsional_invoice_date'] = 'previsional_invoice_date'
        return res
