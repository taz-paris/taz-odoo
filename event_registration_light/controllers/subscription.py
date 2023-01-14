from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
#from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang
#from odoo.tools import lazy

import babel.dates

class EventRegistrationLightController(http.Controller):

    @http.route(['/eventlight/<model("event.event"):event>/registration/new'], type='http', auth="public", methods=['GET'])
    def registration_form(self, event):
        #TODO - contrôle places restreintes
        #TODO - contrôle uuid de l'invitation
        #TODO - refuser accès si l'evènement est passé
        #availability_check = True
        #if event.seats_limited:
            # count registration with state = open
            # if seats_limit overpassaed => return "no seat availlable" page
        return request.env['ir.ui.view']._render_template("event_registration_light.registration_form", {
            'event': event,
            'formated_dates' : self.get_formated_date(event),
        })

    @http.route(['/eventlight/<model("event.event"):event>/registration/submit'], type='http', auth="public", methods=['POST'])
    def registration_submit(self, event, **post):
        return request.env['ir.ui.view']._render_template("event_registration_light.registration_submit")


    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('wide', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s %s') % (start_date.strftime("%e"), month, start_date.strftime("%Y"))
