import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crm_fb_app_id = fields.Char(string='App ID', related="company_id.crm_fb_app_id", readonly=False)
    crm_fb_app_secret = fields.Char(string='App Secret', related="company_id.crm_fb_app_secret", readonly=False)
    crm_fb_access_token = fields.Char(string='Access Token', related="company_id.crm_fb_access_token", readonly=False)

    def action_get_access_token(self):
        redirect_url = "%s/crm_facebook_leads/auth" % (self.env['ir.config_parameter'].get_param('web.base.url'))
        auth_url = 'https://www.facebook.com/dialog/oauth?response_type=token&client_id={}&redirect_uri={}&scope={}&state=cid:{}'.format(
            self.crm_fb_app_id,
            redirect_url,
            'leads_retrieval,pages_manage_ads,pages_read_engagement,ads_management,business_management,pages_show_list',
            self.company_id.id,
        )

        res = {
            'name': 'Facebook Authentication',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': auth_url
        }
        return res

    def action_get_facebook_pages(self):
        r = requests.get("https://graph.facebook.com/v19.0/me/accounts",
                         params={'access_token': self.crm_fb_access_token}).json()
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        if not r.get('data'):
            return
        for p in r['data']:
            if not self.env['crm.facebook.page'].sudo().search([('name', '=', p.get('id'))]):
                self.env['crm.facebook.page'].sudo().create({
                    'label': p.get('name'),
                    'name': p.get('id'),
                    'access_token': p.get('access_token'),
                    'company_id': self.company_id.id,
                })
        action = self.env.ref('vkd_crm_facebook_leads.action_crm_facebook_page').read()[0]
        return action

    @api.depends('crm_fb_access_token')
    def _get_access_token_state(self):
        if not self.crm_fb_access_token:
            self.crm_fb_access_token_state = 'invalid'
            self.crm_fb_access_token_state_message = 'No Access Token provided'
        if not (self.crm_fb_app_id and self.crm_fb_app_secret):
            self.crm_fb_access_token_state = 'unknown'
            self.crm_fb_access_token_state_message = 'App ID and App Secret are required to debug access token'
            return
        r = requests.get("https://graph.facebook.com/v19.0/debug_token", params={'input_token': self.crm_fb_access_token,
                                                                                'access_token': '|'.join(
                                                                                    [self.crm_fb_app_id,
                                                                                     self.crm_fb_app_secret])}).json()
        if r.get('error') or r.get('data', []).get('error'):
            self.crm_fb_access_token_state = 'invalid'
            self.crm_fb_access_token_state_message = r.get('error') and r['error']['message'] or r['data']['error'][
                'message']
            return
        # Probably covered by previous condition
        if not r['data']['is_valid']:
            self.crm_fb_access_token_state = 'invalid'
            return
        if r['data']['type'] != 'USER':
            self.crm_fb_access_token_state = 'invalid'
            self.crm_fb_access_token_state_message = 'Token is of type %s. Must be of type USER' % (r['data']['type'])
            return
        if r['data']['expires_at'] != 0:
            self.crm_fb_access_token_state = 'invalid'
            self.crm_fb_access_token_state_message = 'You need a long-lived access token.'
            return
        scopes = r['data']['scopes']
        if any([scope not in scopes for scope in
                ('leads_retrieval', 'pages_manage_ads', 'pages_read_engagement', 'ads_management')]):
            self.crm_fb_access_token_state = 'invalid'
            self.crm_fb_access_token_state_message = 'Missing permissions: %s' % (', '.join(
                [scope for scope in ('leads_retrieval', 'pages_manage_ads', 'pages_read_engagement', 'ads_management')
                 if scope not in scopes]))
            return
        self.crm_fb_access_token_state = 'valid'
        self.crm_fb_access_token_state_message = ''
