from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    unit_price_aud = fields.Float(string='Unit Price AUD', readonly=True)
    unit_price_usd = fields.Float(string='Unit Price USD', readonly=True)
