# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    crm_fb_app_id = fields.Char(string='App ID', required=True, readonly=False)
    crm_fb_app_secret = fields.Char(string='App Secret', required=True, readonly=False)
    crm_fb_access_token = fields.Char(string='Access Token', required=True, readonly=False)
