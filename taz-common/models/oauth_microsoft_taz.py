# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import requests
import werkzeug.http

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.auth_signup.models.res_users import SignupError

import datetime

from odoo.addons import base
base.models.res_users.USER_PRIVATE_FIELDS.append('oauth_access_token')
base.models.res_users.USER_PRIVATE_FIELDS.append('oauth_refresh_token')#ADU

import logging
_logger = logging.getLogger(__name__)

class OAuthResUsers(models.Model):
    _inherit = 'res.users' #addons/auth_oauth/models/res_users.py

    oauth_token_expires_at = fields.Char("Date d'expiration du token") #ADU
    oauth_refresh_token = fields.Char("Refresh token") #ADU

    def _auth_oauth_rpc(self, endpoint, access_token):
        if self.env['ir.config_parameter'].sudo().get_param('auth_oauth.authorization_header'):
            response = requests.get(endpoint, headers={'Authorization': 'Bearer %s' % access_token}, timeout=10)
        else:
            response = requests.get(endpoint, params={'access_token': access_token}, timeout=10)

        if response.ok: # nb: could be a successful failure
            return response.json()

        auth_challenge = werkzeug.http.parse_www_authenticate_header(
            response.headers.get('WWW-Authenticate'))
        if auth_challenge.type == 'bearer' and 'error' in auth_challenge:
            return dict(auth_challenge)

        return {'error': 'invalid_request'}


    @api.model
    def _auth_oauth_validate(self, provider, access_token):
        """ return the validation data corresponding to the access token """
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = {} #self._auth_oauth_rpc(oauth_provider.validation_endpoint, access_token) #ADU
        if validation.get("error"):
            raise Exception(validation['error'])
        if oauth_provider.data_endpoint:
            data = self._auth_oauth_rpc(oauth_provider.data_endpoint, access_token)
            validation.update(data)
        # unify subject key, pop all possible and get most sensible. When this
        # is reworked, BC should be dropped and only the `sub` key should be
        # used (here, in _generate_signup_values, and in _auth_oauth_signin)
        subject = next(filter(None, [
            validation.pop(key, None)
            for key in [
                'sub', # standard
                'id', # google v1 userinfo, facebook opengraph
                'user_id', # google tokeninfo, odoo (tokeninfo)
            ]
        ]), None)
        if not subject:
            raise AccessDenied('Missing subject identity')
        validation['user_id'] = subject

        return validation

    @api.model
    def _generate_signup_values(self, provider, validation, params):
        oauth_uid = validation['user_id']
        #email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        email = validation.get('mail', 'provider_%s_user_%s' % (provider, oauth_uid)) #ADU
        #name = validation.get('name', email)
        name = validation.get('displayName', email) #ADU
        return {
            'name': name,
            'login': email,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': params['access_token'],
            'active': True,
        }

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oauth_uid = validation['user_id']
        _logger.info(validation)
        try:
            oauth_user = self.search([("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_user:#ADU
                oauth_user = self.search([("email", "=", validation['mail'])]) #ADU
            if not oauth_user:
                raise AccessDenied()
            assert len(oauth_user) == 1
            d = datetime.datetime.now() + datetime.timedelta(seconds=int(params['expires_in']))#ADU
            expire_date = d.isoformat()#ADU
            oauth_user.write({
                'oauth_access_token': params['access_token'], 
                'oauth_uid':oauth_uid, 
                'oauth_token_expires_at' : expire_date,
                #'oauth_refresh_token' : params['refresh_token'], #MS ne retourne pas de refresh_token si offline_access n'est pas intégré au scope
                }) #ADU
            return oauth_user.login
        except AccessDenied as access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = json.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(provider, validation, params)
            try:
                login, _ = self.signup(values, token)
                return login
            except (SignupError, UserError):
                raise access_denied_exception

