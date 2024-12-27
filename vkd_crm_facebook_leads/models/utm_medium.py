from odoo import models, fields, api


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    facebook_ad_id = fields.Char(string='Facebook Ad ID')

    _sql_constraints = [
        ('facebook_ad_unique', 'unique(facebook_ad_id)',
         'This Facebook Ad already exists!')
    ]
