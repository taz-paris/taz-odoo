from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
#from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang
#from odoo.tools import lazy

import logging
_logger = logging.getLogger(__name__)
import babel.dates

class EventRegistrationLightController(http.Controller):

    @http.route(['/eventlight/<model("event.event"):event>/registration/new'], type='http', auth="public", methods=['GET'])
    def registration_form(self, event):
        #TODO - contrôle uuid de l'invitation
        #TODO : envoyer un lien d'annulation par mail
        #availability_check = True
        #if event.seats_limited:
            # count registration with state = open
            # if seats_limit overpassaed => return "no seat availlable" page
        if not event.event_registrations_open :
            return "Les inscription ne sont pas ouvertes pour cet évènement."
        return request.env['ir.ui.view']._render_template("event_registration_light.registration_form", {
            'event': event,
            'formated_dates' : self.get_formated_date(event),
        })

    @http.route(['/eventlight/<model("event.event"):event>/registration/submit'], type='http', auth="public", methods=['POST'])
    def registration_submit(self, event, **post):
        if not event.event_registrations_open : #TODO : si on veut que ça restourne False si le nombre de place max est réservé... il va falloir créer un ticket en plus de la resgitration
            return "Les inscription ne sont pas ouvertes pour cet évènement."

        if not 'email' in post.keys() or  not post['email']:
            return "Pas d'adresse email => inscirption KO"
        email = post['email']
        _logger.info(email)
        first_name = post['first_name']
        name = post['name']
        registrations = request.env['event.registration'].search([('event_id', '=', event.id)])
        target = False
        for reg in registrations :
            if reg['email'] == email :
                target = reg
                break
            if reg['partner_id']:
                if reg['partner_id'].email == email or reg['partner_id'].personal_email == email or (reg['partner_id'].former_email_address and (email in reg['partner_id'].former_email_address)) :
                    target = reg
                    break
        if target :
            target.state = "open"
        else :
            partner = request.env['res.partner'].search([('email', '=', email), ('active', '=', True)])
            if not partner :
                partner = request.env['res.partner'].search([('personal_email', '=', email), ('active', '=', True)])
            if not partner :
                partner = request.env['res.partner'].search([('former_email_address', 'in', email), ('active', '=', True)])
            if len(partner) >= 1 :
                partner_id = partner[0].id
            else :
                partner_id = False
                # TODO : est-ce qu'on le crée avec un user dédié et/ou on le top "créé suite à inscription event" ==> si un rebot nous pollue àa permettrait de les repérer

            #create registration
            target = request.env['event.registration'].create({'event_id' : event.id, 'partner_id' : partner_id, 'email' : email, 'name' : first_name + " " + name, 'state' : 'open'})
        return request.env['ir.ui.view']._render_template("event_registration_light.registration_submit")


    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('wide', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s %s') % (start_date.strftime("%e"), month, start_date.strftime("%Y"))
