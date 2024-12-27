from odoo import fields, models, api


class UtmAdset(models.Model):
    _name = 'utm.adset'
    _description = 'Utm Adset'

    name = fields.Char()
    facebook_adset_id = fields.Char()

    _sql_constraints = [
        ('facebook_adset_unique', 'unique(facebook_adset_id)',
         'This Facebook AdSet already exists!')
    ]
