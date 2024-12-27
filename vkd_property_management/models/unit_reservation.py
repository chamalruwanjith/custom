from datetime import timedelta, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UnitReservation(models.Model):
    _name = "unit.reservation"
    _inherit = 'mail.thread'
    _rec_name = "reservation_id"
    _description = "UnitReservation"

    reservation_id = fields.Char(string="Reservation ID", readonly=True, copy=False, default='New')
    sale_agent_id = fields.Many2one('sale.agent', string="Agent", required=True, tracking=True)
    unit_details_id = fields.Many2one('unit.details', string="Unit", required=True, tracking=True)
    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', required=True)
    floor_details_id = fields.Many2one(comodel_name='floor.details', string='Floor')
    reserved_date = fields.Date(string="Hold Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", compute="_compute_expiration_date", store=True)
    reservation_status = fields.Selection([
        ('draft', 'Draft'),
        ('hold', 'Hold'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('expired', 'Expired'),
        ('cancel', 'Cancel'),
        ('reset', 'Reset to Draft'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        sale_agent_id = vals.get('sale_agent_id')
        apartment_id = vals.get('apartment_details_id')
        if sale_agent_id and apartment_id:
            hold_limit = int(
                self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit'))
            current_holds = self.env['unit.reservation'].search_count([
                ('sale_agent_id', '=', sale_agent_id),
                ('apartment_details_id', '=', apartment_id),
                ('reservation_status', '=', 'hold')
            ])
            if current_holds >= hold_limit:
                agent = self.env['sale.agent'].browse(sale_agent_id)
                apartment = self.env['apartment.details'].browse(apartment_id)
                error_message = _(
                    'The agent %s has reached the hold limit of %s units for the apartment %s.'
                ) % (agent.full_name, hold_limit, apartment.apartment_name)
                raise ValidationError(error_message)
        if vals.get('reservation_id', 'New') == 'New':
            vals['reservation_id'] = self.env['ir.sequence'].next_by_code('unit.reservation') or 'New'
        return super(UnitReservation, self).create(vals)

    def action_unit_hold(self):
        hold_limit = int(self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit'))
        current_holds = self.env['unit.reservation'].search_count([
            ('sale_agent_id', '=', self.sale_agent_id.id),
            ('apartment_details_id', '=', self.apartment_details_id.id),
            ('reservation_status', '=', 'hold')
        ])
        if current_holds >= hold_limit:
            error_message = _(
                'The agent %s has reached the hold limit of %s units for the apartment %s.'
            ) % (self.sale_agent_id.full_name, hold_limit, self.apartment_details_id.name)
            raise ValidationError(error_message)
        self.write({'reservation_status': 'hold', 'reserved_date': date.today()})
        self._update_unit_status('hold')

        return True

    def action_unit_reserve(self):
        self.write({'reservation_status': 'reserved'})
        self._update_unit_status('reserved')

    def action_set_sold(self):
        self.write({'reservation_status': 'sold'})
        self._update_unit_status('sold')

    def action_set_cancel(self):
        self.write({'reservation_status': 'cancel'})
        self._update_unit_status('available')

    def action_set_reset(self):
        self.write({'reservation_status': 'draft'})
        self._update_unit_status('available')

    def _update_unit_status(self, status):
        if self.unit_details_id:
            status_map = {
                'hold': 'hold',
                'reserved': 'reserved',
                'sold': 'sold',
                'expired': 'available',
                'cancel': 'available',
                'reset': 'available'
            }
            new_status = status_map.get(status, 'available')
            self.unit_details_id.write({'unit_status': new_status})

    @api.depends('reserved_date')
    def _compute_expiration_date(self):
        for record in self:
            if record.reserved_date:
                hold_expiration_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_expiration_days'))
                expiration_date = fields.Date.from_string(record.reserved_date) + timedelta(days=hold_expiration_days)
                record.expiration_date = fields.Date.to_string(expiration_date)
            else:
                record.expiration_date = False

    @api.model
    def check_hold_expiration(self):
        today = date.today()
        reservations = self.search([('reservation_status', '=', 'hold')])
        for reservation in reservations:
            if reservation.expiration_date and fields.Date.from_string(reservation.expiration_date) < today:
                reservation.write({'reservation_status': 'expired'})
