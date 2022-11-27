from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo import _
import logging
_logger = logging.getLogger(__name__)

from odoo.addons.web.controllers import utils as mainWebController

#OVERRIDE : odoo/addons/web/controllers/utils.py
# Enable a new case : multiple view_id, multiple view_mode
def new_generate_views(action):
    """
    While the server generates a sequence called "views" computing dependencies
    between a bunch of stuff for views coming directly from the database
    (the ``ir.actions.act_window model``), it's also possible for e.g. buttons
    to return custom view dictionaries generated on the fly.

    In that case, there is no ``views`` key available on the action.

    Since the web client relies on ``action['views']``, generate it here from
    ``view_mode`` and ``view_id``.

    :param dict action: action descriptor dictionary to generate a views key for
    """
    # providing at least one view mode is a requirement, not an option
    #_logger.info('============ debut generate_views')
    view_modes = action['view_mode'].split(',')

    view_ids = action.get('view_id') or False

    if len(view_modes) > 1:
        if view_ids:
            if not (isinstance(view_ids, (list, tuple))) or (len(view_modes) != len(view_ids)):
                raise ValueError('Non-db action dictionaries, if provide multiple view modes and multiple view ids should provide the same number of values in the "view_mode" (coma separated string) and the "view_id" (view ids list) nodes.'
                             'Got view mode %r and view id %r for action %r' % (view_modes, view_ids, action))
            res = []
            for i in range(len(view_modes)):
                res.append((view_ids[i],view_modes[i]))
            action['views'] = res
        else: 
            action['views'] = [(False, mode) for mode in view_modes]

    else :
        if isinstance(view_ids, (list, tuple)):
            view_ids = view_ids[0]
        action['views'] = [(view_ids, view_modes[0])]

    #_logger.info('========= Views' + str(action['views']))

#_logger.info('================ Override web controller done')
mainWebController.generate_views = new_generate_views
