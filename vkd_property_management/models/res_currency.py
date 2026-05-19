# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = "res.currency"

    bulk_price_line_ids = fields.One2many(comodel_name='bulk.price.line', inverse_name='currency_id',
                                          string="Bulk Price Lines")

    def action_update_bulk_price(self):
        """Apply bulk price increase and refresh all pricelists."""
        UnitDetails = self.env['unit.details']
        BulkPriceLine = self.env['bulk.price.line']

        for currency in self:
            draft_bulk_line = BulkPriceLine.search([
                ('currency_id', '=', currency.id),
                ('bulk_line_status', '=', 'draft')
            ], order='create_date desc', limit=1)

            if not draft_bulk_line:
                raise UserError(f"No draft bulk price line found for currency {currency.name}.")

            bulk_amount = draft_bulk_line.bulk_amount
            apartment_ids = draft_bulk_line.apartment_details_ids.ids

            units = UnitDetails.search([
                ('unit_status', 'in', ['draft', 'available']),
                ('company_id', '=', self.env.company.id),
                ('apartment_details_id', 'in', apartment_ids)
            ])

            if not units:
                raise UserError("No matching units found for the selected apartments.")

            for unit in units:
                if unit.unit_price:
                    unit.unit_price += bulk_amount

            draft_bulk_line.bulk_line_status = 'done'
            currency.action_update_unit_price()

    def action_update_unit_price(self):
        """Update unit fields for the specific currency and refresh pricelists."""
        units = self.env['unit.details'].search([('company_id', '=', self.env.company.id)])
        latest_rate_obj = self.rate_ids.filtered(lambda r: r.company_id == self.env.company).sorted('name',
                                                                                                    reverse=True)[:1]

        company_rate = latest_rate_obj.company_rate if latest_rate_obj else 1.0

        for unit in units:
            if self.name == 'AUD':
                unit.unit_price_aud = unit.unit_price * company_rate
            elif self.name == 'USD':
                unit.unit_price_usd = unit.unit_price * company_rate

            product_template = self.env['product.template'].search([
                ('default_code', '=', unit.unit_code),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if product_template:
                if self.name == 'AUD':
                    product_template.unit_price_aud = unit.unit_price_aud
                elif self.name == 'USD':
                    product_template.unit_price_usd = unit.unit_price_usd

        self._sync_all_unit_pricelists()

    @api.model
    def _sync_all_unit_pricelists(self, products=None):
        """Helper to refresh LKR, USD, and AUD pricelists for the provided products."""
        for curr_name in ['LKR', 'USD', 'AUD']:
            currency = self.search([('name', '=', curr_name)], limit=1)
            if currency:
                currency.update_price_list(products=products)

    def update_price_list(self, products=None):
        """Syncs product prices into the specific currency pricelist."""
        Pricelist = self.env['product.pricelist']
        PricelistItem = self.env['product.pricelist.item']
        ProductTemplate = self.env['product.template']

        if not products:
            products = ProductTemplate.search([('company_id', '=', self.env.company.id)])

        for currency in self:
            plist = Pricelist.search([
                ('name', '=', currency.name),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if not plist:
                plist = Pricelist.create({
                    'name': currency.name,
                    'currency_id': currency.id,
                    'company_id': self.env.company.id,
                })

            for product in products:
                if currency.name == 'LKR':
                    target_price = product.list_price
                elif currency.name == 'USD':
                    target_price = getattr(product, 'unit_price_usd', 0.0)
                elif currency.name == 'AUD':
                    target_price = getattr(product, 'unit_price_aud', 0.0)
                else:
                    target_price = 0.0

                item = PricelistItem.search([
                    ('pricelist_id', '=', plist.id),
                    ('product_tmpl_id', '=', product.id)
                ], limit=1)

                if item:
                    item.write({'fixed_price': target_price})
                else:
                    PricelistItem.create({
                        'pricelist_id': plist.id,
                        'product_tmpl_id': product.id,
                        'fixed_price': target_price,
                        'applied_on': '1_product',
                        'compute_price': 'fixed',
                    })
