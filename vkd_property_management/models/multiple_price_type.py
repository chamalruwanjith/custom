# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MultiplePriceType(models.Model):
    _name = 'multiple.price.type'
    _description = 'Multiple Prices Type'
    _rec_name = 'price_type_name'

    price_type_name = fields.Char(string='Price Type', required=True)
    default_product_pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist')
    usd_product_pricelist_id = fields.Many2one('product.pricelist', string='USD Pricelist')
    aud_product_pricelist_id = fields.Many2one('product.pricelist', string='AUD Pricelist')

    @api.model
    def create(self, vals):
        """Create price type record and automatically generate associated pricelists for Default, USD, and AUD currencies."""
        # 1. Create the price type record first
        record = super(MultiplePriceType, self).create(vals)

        # 2. Fetch necessary currencies
        company_currency = self.env.company.currency_id
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        aud_currency = self.env['res.currency'].search([('name', '=', 'AUD')], limit=1)

        Pricelist = self.env['product.pricelist']

        # 3. Create Default (LKR) Pricelist
        default_pl = Pricelist.create({
            'name': f"{record.price_type_name} (Default)",
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        })

        # 4. Create USD Pricelist
        usd_pl = Pricelist.create({
            'name': f"{record.price_type_name} (USD)",
            'currency_id': usd_currency.id if usd_currency else company_currency.id,
            'company_id': self.env.company.id,
        })

        # 5. Create AUD Pricelist
        aud_pl = Pricelist.create({
            'name': f"{record.price_type_name} (AUD)",
            'currency_id': aud_currency.id if aud_currency else company_currency.id,
            'company_id': self.env.company.id,
        })

        # 6. Link created pricelists back to the type record
        record.write({
            'default_product_pricelist_id': default_pl.id,
            'usd_product_pricelist_id': usd_pl.id,
            'aud_product_pricelist_id': aud_pl.id,
        })

        return record
