# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ApartmentDetails(models.Model):
    _name = 'apartment.details'
    _rec_name = "apartment_name"
    _description = 'Apartment Details'

    apartment_name = fields.Char(string='Apartment Name', required=True)
    apartment_prefix = fields.Char(string='Apartment Code', required=True)
    apartment_image = fields.Binary(string='Apartment Image')
    apartment_type = fields.Selection([('residential', 'Residential'), ('commercial', 'Commercial'), ('land', 'Land')],
                                      string='Apartment Type', required=True)
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City', required=True)
    zip_code = fields.Char(string='Zip Code')
    is_publish = fields.Boolean(string='Publish on Portal', default=False)
    is_active = fields.Boolean(string='Active', default=True, compute='_compute_is_active', store=True)
    unit_details_ids = fields.One2many(comodel_name='unit.details', inverse_name='apartment_details_id', string='Units')
    floor_details_ids = fields.One2many(comodel_name='floor.details', inverse_name='apartment_details_id', string='Floors')
    is_multiple_towers = fields.Boolean(string='Multiple Towers', default=False)
    is_include_villas = fields.Boolean(string='Include Villas', default=False)
    villa_prefix = fields.Char(string='Villa Code')
    tower_details_ids = fields.One2many(comodel_name='tower.details', inverse_name='apartment_details_id', string='Floors')
    prefix_for_villas = fields.Char(string='Code for Villas')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    total_units_count = fields.Integer(string='Total Units', compute='_compute_unit_stats')
    sold_percent = fields.Float(string='Sold %', compute='_compute_unit_stats')
    available_percent = fields.Float(string='Available %', compute='_compute_unit_stats')
    reserved_percent = fields.Float(string='Reserved/Hold %', compute='_compute_unit_stats')

    _sql_constraints = [
        ('apartment_name_unique', 'unique (apartment_name)', "Apartment Name must be unique"),
        ('apartment_prefix_unique', 'unique (apartment_prefix)', "Apartment Code must be unique"),
        ('villa_prefix_unique', 'unique (villa_prefix)', "Villa Code must be unique"),
    ]

    @api.depends('unit_details_ids.unit_status')
    def _compute_is_active(self):
        """Set is_active as True if at least one associated unit has 'available' status."""
        for record in self:
            units = self.env['unit.details'].search([('apartment_details_id', '=', record.id)])
            if any(unit.unit_status == 'available' for unit in units):
                record.is_active = True
            else:
                record.is_active = False

    @api.depends('unit_details_ids.unit_status')
    def _compute_unit_stats(self):
        for record in self:
            units = record.unit_details_ids
            total = len(units)

            if total > 0:
                sold = len(units.filtered(lambda u: u.unit_status == 'sold'))
                available = len(units.filtered(lambda u: u.unit_status == 'available'))
                reserved = len(units.filtered(lambda u: u.unit_status in ['reserved', 'hold', 'special_hold']))

                record.total_units_count = total
                record.sold_percent = (sold / total) * 100
                record.available_percent = (available / total) * 100
                record.reserved_percent = (reserved / total) * 100
            else:
                record.total_units_count = 0
                record.sold_percent = 0.0
                record.available_percent = 0.0
                record.reserved_percent = 0.0

    def action_open_floor_form(self):
        """Opens the form view for the selected floor"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Floor Details'),
            'view_mode': 'form',
            'res_model': 'floor.details',
            'res_id': self.floor_details_ids.id,
            'target': 'new',
        }
