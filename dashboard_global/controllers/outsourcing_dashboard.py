from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
#from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang

import logging
_logger = logging.getLogger(__name__)
import babel.dates

class OutsourcingDashboardController(http.Controller):
    @http.route(['/outsourcingDashboard/<int:company_id>/<int:partner_id>'], type='http', auth='user', methods=['GET'])
    def dashboard(self, company_id, partner_id):
        partner = request.env['res.partner'].browse(partner_id)
        data = self.get_data_dict(company_id, partner_id)
        return request.env['ir.ui.view']._render_template("dashboard_global.outsourcing_dashboard", {
            'data': data.values(),
            'supplier' : partner.sudo().name,
        })

    def get_data_dict(self, company_id, partner_id):
        data = {}
        projects = {}
        project_outsourcing_link_ids = request.env['project.outsourcing.link'].search([('company_id', '=', company_id), ('partner_id', '=', partner_id)])
        for pol in project_outsourcing_link_ids:
            p = pol.project_id
            if p.sudo().stage_id.id in [3, 8, 4]:
                continue
            projects[p.id] = p.sudo().read(['partner_id', 'stage_id', 'number', 'name', 'project_director_employee_id', 'date_start', 'date'])[0]


            projects[p.id]['sale_order_lines'] = []
            sale_order_line_ids = p.sudo().get_sale_order_line_ids()
            sale_order_lines = request.env['sale.order.line'].sudo().browse(sale_order_line_ids)
            for sale_order_line in sale_order_lines:
                d = sale_order_line.sudo().read(['name', 'order_id', 'price_unit', 'product_uom_qty', 'price_subtotal', 'previsional_invoice_date', 'comment'])[0]
                d['invoice_lines'] = []
                for il in sale_order_line.sudo().invoice_lines :
                    if il.parent_state != 'cancel':
                        d['invoice_lines'].append(il.sudo().read(['name', 'ref', 'date', 'price_unit', 'quantity', 'price_subtotal_signed', 'parent_payment_state'])[0])
                projects[p.id]['sale_order_lines'].append(d)


            projects[p.id]['purchase_order_lines'] = []
            purchase_order_line_ids = pol.sudo().get_purchase_order_line_ids() 
            purchase_order_lines = request.env['purchase.order.line'].sudo().browse(purchase_order_line_ids)
            for purchase_order_line in purchase_order_lines:
                d = purchase_order_line.read(['name', 'order_id', 'price_unit', 'product_uom_qty', 'price_subtotal', 'previsional_invoice_date', 'state'])[0]
                d['invoice_lines'] = []
                for il in purchase_order_line.sudo().invoice_lines :
                    if il.parent_state != 'cancel':
                        d['invoice_lines'].append(il.sudo().read(['name', 'ref', 'date', 'price_unit', 'quantity', 'price_subtotal_signed', 'parent_payment_state'])[0])
                projects[p.id]['purchase_order_lines'].append(d)

            

        for pid, pval in projects.items():
            if not pval['partner_id'][0] in data.keys():
                data[pval['partner_id'][0]] = {'name' : pval['partner_id'][1],'projects':[]}
            data[pval['partner_id'][0]]['projects'].append(pval)

        #_logger.info(data.values())
        return data

