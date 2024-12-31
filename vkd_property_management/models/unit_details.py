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
    usable_area = fields.Float(string='Usable Area')
    number_of_floors = fields.Integer(string='Number of Floors')
    number_of_rooms = fields.Integer(string='Number of Rooms')
    number_of_bathrooms = fields.Integer(string='Number of Bathrooms')
    facing_direction = fields.Selection([
        ('north', 'North'),
        ('northeast', 'Northeast'),
        ('east', 'East'),
        ('southeast', 'Southeast'),
        ('south', 'South'),
        ('southwest', 'Southwest'),
        ('west', 'West'),
        ('northwest', 'Northwest'),
        ('north_northeast', 'North-Northeast'),
        ('east_northeast', 'East-Northeast'),
        ('east_southeast', 'East-Southeast'),
        ('south_southeast', 'South-Southeast'),
        ('south_southwest', 'South-Southwest'),
        ('west_southwest', 'West-Southwest'),
        ('west_northwest', 'West-Northwest'),
        ('north_northwest', 'North-Northwest'),
    ], string="Facing Direction")
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    zip_code = fields.Char(string='Zip Code')
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

    def _compute_property_user(self):
        """Set is_property_user based on the current user's group."""
        user = self.env.user
        for record in self:
            if user.has_group('vkd_property_management.group_property_management_admin'):
                record.is_property_user = False
            elif user.has_group('vkd_property_management.group_property_management_user'):
                record.is_property_user = True
            else:
                record.is_property_user = True

    @api.constrains('unit_name', 'floor_details_id')
    def _check_unit_name_uniqueness(self):
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
        using the last two characters of unit_name."""
        for record in self:
            unit_suffix = record.unit_name[-2:] if record.unit_name else ''

            if record.unit_type == 'unit':
                if record.floor_details_id:
                    floor_name = record.floor_details_id.floor_name
                    record.unit_code = f"{floor_name}-{unit_suffix}"
                else:
                    record.unit_code = unit_suffix
            else:
                if record.apartment_details_id:
                    apartment_prefix = record.apartment_details_id.prefix_for_villas or ''
                    record.unit_code = f"{apartment_prefix}-{unit_suffix}"
                else:
                    record.unit_code = unit_suffix

    @api.model
    def create(self, vals):
        """Creates a related product for the unit if it doesn't exist."""
        vals['company_id'] = self.env.company.id
        record = super(UnitDetails, self).create(vals)
        product_template = self.env['product.template']
        existing_product = product_template.search([('default_code', '=', record.unit_code)], limit=1)
        if not existing_product:
            product_vals = {
                'name': record.unit_code,
                'default_code': record.unit_code,
                'type': 'product',
                'list_price': record.unit_price,
                'categ_id': self.env.ref('product.product_category_all').id,
                'company_id': record.company_id.id,
            }
            product_template.create(product_vals)

        return record

    def write(self, vals):
        """Updates the related product when unit details are updated."""
        res = super(UnitDetails, self).write(vals)
        product_template = self.env['product.template']

        for unit in self:
            product = product_template.search([('default_code', '=', unit.unit_code)], limit=1)
            if product:
                product.write({
                    'list_price': unit.unit_price,
                    'company_id': unit.company_id.id,
                })

        return res

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
        self.write({'unit_status': 'available'})

    def action_set_reserved(self):
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
        for unit in self:
            # Check for confirmed sale orders
            sale_orders = self.env['sale.order.line'].search([
                ('product_id.default_code', '=', unit.unit_code)
            ]).mapped('order_id')

            confirmed_orders = sale_orders.filtered(lambda so: so.state == 'sale')
            if confirmed_orders:
                raise ValidationError(
                    _("This unit has a confirmed sale order and cannot be canceled. "
                      "Please handle the sale order(s) before canceling the unit.")
                )

            # Cancel quotation sale orders
            quotation_orders = sale_orders.filtered(lambda so: so.state in ['draft', 'sent'])
            for order in quotation_orders:
                order.action_cancel()

            # Update the unit status
            unit.write({
                'unit_status': 'cancel',
                'is_unit_special_hold': False,
                'is_unit_sold': False,
            })

    def action_set_reset(self):
        self.write({'unit_status': 'draft'})

    def action_set_special_hold(self):
        self.write({'unit_status': 'special_hold', 'is_unit_special_hold': True})

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
        for record in self:
            sale_order_lines = self.env['sale.order.line'].search([
                ('product_id.default_code', '=', record.unit_code)
            ])
            record.sale_order_count = len(sale_order_lines.mapped('order_id'))
