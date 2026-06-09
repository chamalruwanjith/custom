# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnitMultiplePrice(models.Model):
    _name = 'unit.multiple.price'
    _description = 'Unit Multiple Prices'

    unit_details_id = fields.Many2one(comodel_name='unit.details', string='Unit Details', ondelete='cascade')
    unit_price = fields.Float(string='Unit Price LKR')
    unit_price_aud = fields.Float(string='Unit Price AUD', compute='_compute_foreign_prices', store=True)
    unit_price_usd = fields.Float(string='Unit Price USD', compute='_compute_foreign_prices', store=True)
    multiple_price_type_id = fields.Many2one(comodel_name='multiple.price.type', string='Multiple Price')
    house_area = fields.Float(string='House Area(Sqft)')
    room_count = fields.Integer(string='Number of Rooms')
    bathroom_count = fields.Integer(string='Number of Bathrooms')


    @api.model
    def create(self, vals):
        """Create multiple price record, log price history, and sync to associated pricelists."""
        record = super(UnitMultiplePrice, self).create(vals)

        self.env['unit.price.history'].create({
            'unit_details_id': record.unit_details_id.id,
            'price_type': f"{record.multiple_price_type_id.price_type_name} (Multiple)",
            'old_price': 0.0,
            'new_price': record.unit_price,
        })

        record._sync_to_pricelists()
        return record

    def write(self, vals):
        """Update multiple price record, log price changes, and resync pricelists if price or type changed."""
        if 'unit_price' in vals:
            for record in self:
                if record.unit_price != vals.get('unit_price'):
                    self.env['unit.price.history'].create({
                        'unit_details_id': record.unit_details_id.id,
                        'price_type': f"{record.multiple_price_type_id.price_type_name} (Multiple)",
                        'old_price': record.unit_price,
                        'new_price': vals.get('unit_price'),
                    })

        res = super(UnitMultiplePrice, self).write(vals)

        if 'unit_price' in vals or 'multiple_price_type_id' in vals:
            self._sync_to_pricelists()

        return res

    def _sync_to_pricelists(self):
        """Updates or creates pricelist items in the 3 linked pricelists."""
        PricelistItem = self.env['product.pricelist.item']
        ProductTemplate = self.env['product.template']

        for record in self:
            if not record.multiple_price_type_id or not record.unit_details_id:
                continue

            product = ProductTemplate.search([
                ('default_code', '=', record.unit_details_id.unit_code),
                ('company_id', '=', record.unit_details_id.company_id.id)
            ], limit=1)

            if not product:
                continue

            price_type = record.multiple_price_type_id

            def update_pricelist(pricelist_id, price):
                if not pricelist_id:
                    return
                item = PricelistItem.search([
                    ('pricelist_id', '=', pricelist_id.id),
                    ('product_tmpl_id', '=', product.id)
                ], limit=1)

                if item:
                    item.write({'fixed_price': price})
                else:
                    PricelistItem.create({
                        'pricelist_id': pricelist_id.id,
                        'product_tmpl_id': product.id,
                        'fixed_price': price,
                        'applied_on': '1_product',
                    })

            update_pricelist(price_type.default_product_pricelist_id, record.unit_price)
            update_pricelist(price_type.usd_product_pricelist_id, record.unit_price_usd)
            update_pricelist(price_type.aud_product_pricelist_id, record.unit_price_aud)

    @api.depends('unit_price')
    def _compute_foreign_prices(self):
        """Automatically calculate AUD and USD prices based on the latest currency rates."""
        aud_currency = self.env['res.currency'].search([('name', '=', 'AUD')], limit=1)
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        for record in self:
            if not record.unit_price:
                record.unit_price_aud = 0.0
                record.unit_price_usd = 0.0
                continue

            company = record.unit_details_id.company_id or self.env.company

            aud_rate = aud_currency.rate_ids.filtered(lambda r: r.company_id == company).sorted('name', reverse=True)[
                       :1].company_rate if aud_currency else 0.0
            usd_rate = usd_currency.rate_ids.filtered(lambda r: r.company_id == company).sorted('name', reverse=True)[
                       :1].company_rate if usd_currency else 0.0

            record.unit_price_aud = record.unit_price * aud_rate
            record.unit_price_usd = record.unit_price * usd_rate
