from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def action_update_unit_price(self):
        """Update unit prices based on current currency rates."""
        # Filter units by the current company
        units = self.env['unit.details'].search([('company_id', '=', self.env.company.id)])
        latest_rate = self.rate_ids.filtered(lambda r: r.company_id == self.env.company).sorted('name', reverse=True)[
                      :1]

        if not latest_rate:
            raise UserError(f"No rate found for currency {self.name} in the current company.")

        company_rate = latest_rate.company_rate

        for unit in units:
            if self.name == 'AUD':
                unit.unit_price_aud = unit.unit_price * company_rate
            elif self.name == 'USD':
                unit.unit_price_usd = unit.unit_price * company_rate

            # Ensure product_template belongs to the same company
            product_template = self.env['product.template'].search([
                ('default_code', '=', unit.unit_code),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if product_template:
                if self.name == 'AUD':
                    product_template.unit_price_aud = unit.unit_price_aud
                elif self.name == 'USD':
                    product_template.unit_price_usd = unit.unit_price_usd

        self.update_price_list()

    def update_price_list(self):
        """Create and update price lists for AUD and USD, including products with 0.00 value."""
        Pricelist = self.env['product.pricelist']
        PricelistItem = self.env['product.pricelist.item']
        ProductTemplate = self.env['product.template']

        # Filter pricelists and products by the current company
        aud_pricelist = Pricelist.search([
            ('name', '=', 'AUD'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        usd_pricelist = Pricelist.search([
            ('name', '=', 'USD'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not aud_pricelist:
            aud_pricelist = Pricelist.create({
                'name': 'AUD',
                'currency_id': self.env['res.currency'].search([('name', '=', 'AUD')], limit=1).id,
                'company_id': self.env.company.id,
            })

        if not usd_pricelist:
            usd_pricelist = Pricelist.create({
                'name': 'USD',
                'currency_id': self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id,
                'company_id': self.env.company.id,
            })

        products = ProductTemplate.search([('company_id', '=', self.env.company.id)])

        for product in products:
            # Update or create AUD pricelist item
            aud_item = PricelistItem.search([
                ('pricelist_id', '=', aud_pricelist.id),
                ('product_tmpl_id', '=', product.id)
            ], limit=1)

            if aud_item:
                aud_item.fixed_price = product.unit_price_aud or 0.00
            else:
                PricelistItem.create({
                    'pricelist_id': aud_pricelist.id,
                    'product_tmpl_id': product.id,
                    'fixed_price': product.unit_price_aud or 0.00,
                })

            # Update or create USD pricelist item
            usd_item = PricelistItem.search([
                ('pricelist_id', '=', usd_pricelist.id),
                ('product_tmpl_id', '=', product.id)
            ], limit=1)

            if usd_item:
                usd_item.fixed_price = product.unit_price_usd or 0.00
            else:
                PricelistItem.create({
                    'pricelist_id': usd_pricelist.id,
                    'product_tmpl_id': product.id,
                    'fixed_price': product.unit_price_usd or 0.00,
                })
