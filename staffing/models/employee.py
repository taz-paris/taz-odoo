from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

class staffingEmployee(models.Model):
    _inherit = "hr.employee"

    def _sync_user(self, user, employee_has_image=False):
        vals  = super()._sync_user(user, employee_has_image) 
        if user.first_name :
            vals['first_name'] = user.first_name
        if user.partner_id:
            vals['work_contact_id'] = user.partner_id.id

        if not 'work_email' in vals.keys():
            if '@' in user.login:
                vals['work_email'] = user.login
        return vals


    def action_create_user(self):
        vals = super().action_create_user()
        if self.first_name:
            vals['context']['default_first_name'] = self.first_name
        if self.work_contact_id:
            vals['context']['default_partner_id'] = self.work_contact_id
        return vals


    first_name = fields.Char(string="Prénom")

    def name_get(self):
         res = []
         for rec in self:                       
            res.append((rec.id, "%s %s" % (rec.first_name or "", rec.name or "")))
         return res                             
    
    @api.model                              
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []          
        recs = self.browse()    
        if not recs:                    
            recs = self.search(['|', ('first_name', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()     

    def _get_daily_cost(self, date):
        if self.job_id :
            return self.job_id._get_daily_cost(date)
        else :  
            return False


class staffingUsers(models.Model):
    _inherit = "res.users"

    def _get_employee_fields_to_sync(self):
        res = super()._get_employee_fields_to_sync()
        res.append('first_name')
        return res
