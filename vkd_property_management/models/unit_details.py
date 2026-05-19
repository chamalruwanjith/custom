# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError, ValidationError


class UnitDetails(models.Model):
    _name = 'unit.details'
    _inherit = 'mail.thread'
    _rec_name = 'unit_code'
    _description = 'Unit Details'

    unit_name = fields.Char(string='Unit Name', required=True, tracking=True)
    unit_code = fields.Char(string='Unit Code', compute='_compute_unit_code', store=True)
    unit_image = fields.Binary(string='Unit Image')
    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', required=True)
    floor_details_id = fields.Many2one(comodel_name='floor.details', string='Floor')
    unit_price = fields.Float(string='Unit Price LKR', required=True, tracking=True)
    unit_price_aud = fields.Float(string='Unit Price AUD', tracking=True)
    unit_price_usd = fields.Float(string='Unit Price USD', tracking=True)
    unit_address = fields.Char(string='Unit Address')
    total_area = fields.Float(string='Total Area')
    number_of_floors = fields.Integer(string='Number of Floors')
    number_of_rooms = fields.Integer(string='Number of Rooms')
    number_of_bathrooms = fields.Integer(string='Number of Bathrooms')
    facing_direction = fields.Selection([
        ('non_view', 'Non View'),
        ('with_view', 'View'),
        ('paddy_view', 'Paddy View'),
        ('inside_view', 'Inside View'),
        ('lake_view', 'Lake View'),
        ('sea_view', 'Sea View'),
        ('garden_view', 'Garden View'),
        ('pool_view', 'Pool View'),
        ('city_view', 'City View'),
        ('mountain_view', 'Mountain View'),
        ('river_view', 'River View'),
        ('park_view', 'Park View'),
        ('courtyard_view', 'Courtyard View'),
        ('street_view', 'Street View'),
        ('skyline_view', 'Skyline View'),
        ('beach_view', 'Beach View'),
        ('forest_view', 'Forest View'),
        ('golf_view', 'Golf Course View'),
        ('harbor_view', 'Harbor View'),
        ('sunset_view', 'Sunset View'),
        ('airport_view', 'Airport View'),
        ('greenery_view', 'Greenery View'),
    ], string="Facing View")
    special_note = fields.Html(string="Special Notes")
    unit_status = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('hold', 'Hold'),
        ('special_hold', 'Special Hold'),
        ('reserved', 'Tentatively Sold'),
        ('sold', 'Sold'),
        ('cancel', 'Cancel'),
        ('reset', 'Reset to Draft'),
    ], string='Status', default='draft', tracking=True)
    unit_images_1 = fields.Binary(string='Image 1')
    unit_images_2 = fields.Binary(string='Image 2')
    unit_images_3 = fields.Binary(string='Image 3')
    unit_images_4 = fields.Binary(string='Image 4')
    tower_details_id = fields.Many2one(comodel_name='tower.details', string='Tower')
    is_multiple_tower_apartment = fields.Boolean(string='Multiple Tower Apartment', default=False)
    unit_type = fields.Selection([('unit', 'Unit'), ('villa', 'Villa')], string='Type', default='unit', required=True)
    is_include_villas = fields.Boolean(string='Include Villas', default=False)
    is_multiple_floors = fields.Boolean(string='Multiple Floors', default=False)
    floor_details_ids = fields.Many2many(comodel_name='floor.details', inverse_name='floor_details_id', string='Floors',
                                         required=True)
    sale_order_count = fields.Integer(string='Sale Orders', compute='_compute_sale_order_count')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    is_unit_sold = fields.Boolean(string='Unit Sold', default=False)
    is_unit_special_hold = fields.Boolean(string='Unit Special Hold', default=False)
    is_property_user = fields.Boolean(string='Property User', default=True, compute='_compute_property_user')
    multiple_price_ids = fields.One2many(comodel_name='unit.multiple.price', inverse_name='unit_details_id',
                                         string='Multiple Prices')
    villa_type = fields.Selection([('villa', 'Villa'), ('house', 'House'), ('cottage', 'Cottage')], string='Villa Type')
    house_area = fields.Float(string='House Area(Sqft)')
    total_area_uom_id = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure")
    garden_area = fields.Float(string='Garden Area(Sqft)')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['company_id'] = self.env.company.id

        records = super(UnitDetails, self).create(vals_list)

        product_template_env = self.env['product.template']
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        batch_products = product_template_env.browse()

        for record in records:
            if record.unit_price > 0:
                record._update_currency_prices()

                self.env['unit.price.history'].create({
                    'unit_details_id': record.id,
                    'price_type': 'Base Price',
                    'old_price': 0.0,
                    'new_price': record.unit_price,
                })

            existing_product = product_template_env.search([('default_code', '=', record.unit_code)], limit=1)

            if not existing_product:
                product_vals = {
                    'name': record.unit_code,
                    'default_code': record.unit_code,
                    'type': 'product',
                    'list_price': record.unit_price,
                    'unit_price_aud': record.unit_price_aud,
                    'unit_price_usd': record.unit_price_usd,
                    'categ_id': self.env.ref('product.product_category_all').id,
                    'company_id': record.company_id.id,
                }
                new_product = product_template_env.create(product_vals)
                batch_products += new_product

                if warehouse:
                    self.env['stock.quant'].with_context(inventory_mode=True).create({
                        'product_id': new_product.product_variant_id.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'inventory_quantity': 1.0,
                    })._apply_inventory()
            else:
                batch_products += existing_product

        if batch_products:
            self.env['res.currency']._sync_all_unit_pricelists(products=batch_products)

        for record in records:
            if record.multiple_price_ids:
                record.multiple_price_ids._sync_to_pricelists()

        return records

    def write(self, vals):
        """Updates unit, logs price history, and synchronizes all pricelists."""
        tracked_fields = ['unit_price', 'unit_price_aud', 'unit_price_usd', 'unit_status']
        if any(field in vals for field in tracked_fields):
            clean_context = dict(self.env.context)
            clean_context.pop('tracking_disable', None)
            clean_context.pop('mail_notrack', None)
            self = self.with_context(clean_context)

        if 'unit_price' in vals:
            for unit in self:
                if unit.unit_price != vals.get('unit_price'):
                    self.env['unit.price.history'].create({
                        'unit_details_id': unit.id,
                        'price_type': 'Base Price',
                        'old_price': unit.unit_price,
                        'new_price': vals.get('unit_price'),
                    })

        res = super(UnitDetails, self).write(vals)

        if 'unit_price' in vals:
            self._update_currency_prices()
            self.env['res.currency']._sync_all_unit_pricelists()

        product_template = self.env['product.template']
        for unit in self:
            product = product_template.search([('default_code', '=', unit.unit_code)], limit=1)
            if product:
                product.write({
                    'list_price': unit.unit_price,
                    'unit_price_aud': unit.unit_price_aud,
                    'unit_price_usd': unit.unit_price_usd,
                    'company_id': unit.company_id.id,
                })

        return res

    def _update_currency_prices(self):
        """Fetches the latest rates and updates the AUD and USD prices on the unit."""
        aud_currency = self.env['res.currency'].search([('name', '=', 'AUD')], limit=1)
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        for unit in self:
            if not unit.unit_price:
                unit.unit_price_aud = 0.0
                unit.unit_price_usd = 0.0
                continue

            aud_rate = aud_currency.rate_ids.filtered(lambda r: r.company_id == unit.company_id).sorted('name',
                                                                                                        reverse=True)[
                       :1].company_rate if aud_currency else 0.0
            usd_rate = usd_currency.rate_ids.filtered(lambda r: r.company_id == unit.company_id).sorted('name',
                                                                                                        reverse=True)[
                       :1].company_rate if usd_currency else 0.0

            unit.unit_price_aud = unit.unit_price * aud_rate
            unit.unit_price_usd = unit.unit_price * usd_rate

    def _compute_property_user(self):
        """Set is_property_user based on the current user's group."""
        user = self.env.user
        for record in self:
            if user.has_group('vkd_property_management.group_property_management_manager'):
                record.is_property_user = False
            elif user.has_group('vkd_property_management.group_property_management_user'):
                record.is_property_user = True
            else:
                record.is_property_user = True

    @api.constrains('unit_name', 'floor_details_id')
    def _check_unit_name_uniqueness(self):
        """Ensure unit name is unique within the same floor."""
        for record in self:
            duplicate = self.search([
                ('unit_name', '=', record.unit_name),
                ('floor_details_id', '=', record.floor_details_id.id),
                ('id', '!=', record.id)
            ])
            if duplicate:
                raise ValidationError("The unit name must be unique within the same floor.")

    @api.depends('floor_details_id', 'unit_name', 'unit_type', 'apartment_details_id')
    def _compute_unit_code(self):
        """Generates unit code based on type, floor, or apartment details,
        using the last two characters of unit_name with 'U' prefix."""
        for record in self:
            unit_suffix = f"{record.unit_name[-2:]}" if record.unit_name else ''

            if record.unit_type == 'unit':
                if record.floor_details_id:
                    floor_name = record.floor_details_id.floor_name
                    record.unit_code = f"{floor_name}/{unit_suffix}"
                else:
                    record.unit_code = unit_suffix
            else:
                if record.apartment_details_id:
                    apartment_prefix = record.apartment_details_id.prefix_for_villas or ''
                    record.unit_code = f"{apartment_prefix}/{unit_suffix}"
                else:
                    record.unit_code = unit_suffix

    @api.model
    def _update_missing_units(self):
        """Creates or updates products for all units."""
        units = self.search([])
        product_template = self.env['product.template']

        for unit in units:
            product = product_template.search([('default_code', '=', unit.unit_code)], limit=1)

            if product:
                product.write({
                    'name': unit.unit_code,
                    'list_price': unit.unit_price,
                    'company_id': unit.company_id.id,
                })
            else:
                product_template.create({
                    'name': unit.unit_code,
                    'default_code': unit.unit_code,
                    'type': 'product',
                    'list_price': unit.unit_price,
                    'categ_id': self.env.ref('product.product_category_all').id,
                    'company_id': unit.company_id.id,
                })

    def action_set_available(self):
        """Mark unit as available for sale and clear special hold flag."""
        self.write({'unit_status': 'available', 'is_unit_special_hold': False})

    def action_set_reserved(self):
        """Open customer selection wizard to tentatively sell (reserve) the unit."""
        self.ensure_one()

        return {
            'name': _('Select Customer'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.customer.select',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_unit_details_id': self.id,
            }
        }

    def action_set_cancel(self):
        """Cancel unit, validate no confirmed sale orders exist, and cancel any quotation orders."""
        for unit in self:
            sale_orders = self.env['sale.order.line'].search([
                ('product_id.default_code', '=', unit.unit_code)
            ]).mapped('order_id')

            confirmed_orders = sale_orders.filtered(lambda so: so.state == 'sale')
            if confirmed_orders:
                raise ValidationError(
                    _("This unit has a confirmed sale order and cannot be canceled. "
                      "Please handle the sale order(s) before canceling the unit.")
                )

            quotation_orders = sale_orders.filtered(lambda so: so.state in ['draft', 'sent'])
            for order in quotation_orders:
                order.action_cancel()

            unit.write({
                'unit_status': 'cancel',
                'is_unit_special_hold': False,
                'is_unit_sold': False,
            })
            self._update_unit_activity('cancel')

    def action_set_reset(self):
        """Reset unit status back to draft."""
        self.write({'unit_status': 'draft'})

    def action_set_special_hold(self):
        """Mark unit with special hold status and log activity."""
        self.write({'unit_status': 'special_hold', 'is_unit_special_hold': True})
        self._update_unit_activity('special_hold')

    def _update_unit_activity(self, activity_type):
        """Create an activity log entry for unit status changes."""
        self.ensure_one()
        self.env['unit.activity'].create({
            'user_id': self.env.uid,
            'unit_details_id': self.id,
            'apartment_details_id': self.apartment_details_id.id,
            'activity_type': activity_type,
        })

    @api.onchange('apartment_details_id')
    def _onchange_apartment_details_id(self):
        """Updates tower and villa details based on the apartment."""
        for record in self:
            if record.apartment_details_id:
                record.is_multiple_tower_apartment = record.apartment_details_id.is_multiple_towers
                record.is_include_villas = record.apartment_details_id.is_include_villas
            else:
                record.is_multiple_tower_apartment = False
                record.is_include_villas = False

    def action_open_products(self):
        """Open the associated product template form view for this unit."""
        self.ensure_one()
        product = self.env['product.template'].search([('default_code', '=', self.unit_code)], limit=1)
        if product:
            return {
                'name': 'Products',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': product.id,
            }

    def action_open_sale_orders(self):
        """Open all sale orders associated with this unit."""
        self.ensure_one()

        sale_order_lines = self.env['sale.order.line'].search([
            ('product_id.default_code', '=', self.unit_code)
        ])
        sale_orders = sale_order_lines.mapped('order_id')

        if sale_orders:
            return {
                'name': _('Sale Orders'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', sale_orders.ids)],
            }

    @api.depends('unit_code')
    def _compute_sale_order_count(self):
        """Calculate the number of sale orders referencing this unit."""
        for record in self:
            sale_order_lines = self.env['sale.order.line'].search([
                ('product_id.default_code', '=', record.unit_code)
            ])
            record.sale_order_count = len(sale_order_lines.mapped('order_id'))
