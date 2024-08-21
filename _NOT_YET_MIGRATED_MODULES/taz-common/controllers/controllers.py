# -*- coding: utf-8 -*-
# from odoo import http


# class Taz-common(http.Controller):
#     @http.route('/taz-common/taz-common', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/taz-common/taz-common/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('taz-common.listing', {
#             'root': '/taz-common/taz-common',
#             'objects': http.request.env['taz-common.taz-common'].search([]),
#         })

#     @http.route('/taz-common/taz-common/objects/<model("taz-common.taz-common"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('taz-common.object', {
#             'object': obj
#         })
