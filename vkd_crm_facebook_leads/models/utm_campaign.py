from odoo import models, fields, api


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    facebook_campaign_id = fields.Char(string='Facebook Campaign ID')

    _sql_constraints = [
        ('facebook_campaign_unique', 'unique(facebook_campaign_id)',
         'This Facebook Campaign already exists!')
    ]
