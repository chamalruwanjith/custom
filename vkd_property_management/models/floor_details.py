# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FloorDetails(models.Model):
    _name = 'floor.details'
    _rec_name = 'floor_name'
    _description = 'Floor Details'

    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', required=True)
    floor_name = fields.Char(string='Floor Number', required=True)
    floor_image = fields.Binary(string='Floor Image')
    is_active = fields.Boolean(string='Active', default=True, compute='_compute_is_active', store=True)
    unit_details_ids = fields.One2many(comodel_name='unit.details', inverse_name='floor_details_id', string='Units')
    total_units = fields.Integer(string='Total Units', compute='_compute_total_units', store=True)
    available_units = fields.Integer(string='Available Units', compute='_compute_available_units', store=True)
    reserved_units = fields.Integer(string='Reserved Units', compute='_compute_reserved_units', store=True)
    sold_units = fields.Integer(string='Sold Units', compute='_compute_sold_units', store=True)
    tower_details_id = fields.Many2one(comodel_name='tower.details', string='Tower')
    is_multiple_tower_apartment = fields.Boolean(string='Multiple Tower Apartment', default=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('floor_name_unique', 'unique(floor_name)',
         'The floor name must be unique.')
    ]

    @api.onchange('apartment_details_id', 'tower_details_id')
    def _onchange_apartment_details_id(self):
        """Auto-generate floor name based on apartment/tower prefix and sequential numbering."""
        if self.apartment_details_id:
            if self.apartment_details_id.is_multiple_towers:
                if self.tower_details_id and self.tower_details_id.tower_prefix:
                    tower_prefix = self.tower_details_id.tower_prefix
                    existing_floors = self.env['floor.details'].search([
                        ('apartment_details_id', '=', self.apartment_details_id.id),
                        ('tower_details_id', '=', self.tower_details_id.id),
                        ('floor_name', 'ilike', f'{tower_prefix}/F%')
                    ])
                    max_number = 0
                    for floor in existing_floors:
                        try:
                            number_part = floor.floor_name.split('/F')[-1]
                            max_number = max(max_number, int(number_part))
                        except ValueError:
                            pass
                    next_number = max_number + 1
                    self.floor_name = f'{tower_prefix}/F{next_number:02d}'
                else:
                    self.floor_name = ''
            else:
                apartment_prefix = self.apartment_details_id.apartment_prefix
                if apartment_prefix:
                    existing_floors = self.env['floor.details'].search([
                        ('apartment_details_id', '=', self.apartment_details_id.id),
                        ('floor_name', 'ilike', f'{apartment_prefix}/F%')
                    ])
                    max_number = 0
                    for floor in existing_floors:
                        try:
                            number_part = floor.floor_name.split('/F')[-1]
                            max_number = max(max_number, int(number_part))
                        except ValueError:
                            pass
                    next_number = max_number + 1
                    self.floor_name = f'{apartment_prefix}/F{next_number:02d}'
                else:
                    self.floor_name = ''
            self.is_multiple_tower_apartment = self.apartment_details_id.is_multiple_towers
        else:
            self.floor_name = ''
            self.is_multiple_tower_apartment = False

    @api.depends('unit_details_ids.unit_status')
    def _compute_is_active(self):
        """Set floor as active if at least one associated unit has 'available' status."""
        for record in self:
            units = self.env['unit.details'].search([('floor_details_id', '=', record.id)])
            if any(unit.unit_status == 'available' for unit in units):
                record.is_active = True
            else:
                record.is_active = False

    @api.depends('unit_details_ids')
    def _compute_total_units(self):
        """Calculate total number of units associated with the floor."""
        for record in self:
            record.total_units = len(record.unit_details_ids)

    @api.depends('unit_details_ids')
    def _compute_available_units(self):
        """Count units with 'available' status on the floor."""
        for record in self:
            record.available_units = len(record.unit_details_ids.filtered(lambda unit: unit.unit_status == 'available'))

    @api.depends('unit_details_ids')
    def _compute_reserved_units(self):
        """Count units with 'reserved' status on the floor."""
        for record in self:
            record.reserved_units = len(record.unit_details_ids.filtered(lambda unit: unit.unit_status == 'reserved'))

    @api.depends('unit_details_ids')
    def _compute_sold_units(self):
        """Count units with 'sold' status on the floor."""
        for record in self:
            record.sold_units = len(record.unit_details_ids.filtered(lambda unit: unit.unit_status == 'sold'))
