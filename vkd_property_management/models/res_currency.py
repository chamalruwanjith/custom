from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = "res.currency"

    bulk_price_line_ids = fields.One2many(comodel_name='bulk.price.line', inverse_name='currency_id',
                                          string="Bulk Price Lines")

    def action_update_bulk_price(self):
        UnitDetails = self.env['unit.details']
        BulkPriceLine = self.env['bulk.price.line']

        for currency in self:
            # Step 1: Get the latest draft bulk price line for this currency
            draft_bulk_line = BulkPriceLine.search([
                ('currency_id', '=', currency.id),
                ('bulk_line_status', '=', 'draft')
            ], order='create_date desc', limit=1)

            if not draft_bulk_line:
                raise UserError(f"No draft bulk price line found for currency {currency.name}.")

            bulk_amount = draft_bulk_line.bulk_amount
            apartment_ids = draft_bulk_line.apartment_details_ids.ids

            # Step 2: Find units in draft/available state linked to those apartments
            domain = [
                ('unit_status', 'in', ['draft', 'available']),
                ('company_id', '=', self.env.company.id),
                ('apartment_details_id', 'in', apartment_ids)
            ]
            units = UnitDetails.search(domain)

            if not units:
                raise UserError("No matching units found for the selected apartments.")

            # Step 3: Update unit_price by adding bulk_amount
            for unit in units:
                if unit.unit_price:
                    unit.unit_price += bulk_amount

            # Step 4: Mark the bulk price line as done
            draft_bulk_line.bulk_line_status = 'done'

            # Step 5: Call currency-level price update logic
            currency.action_update_unit_price()

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
