# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class UnitActivity(models.Model):
    _name = "unit.activity"
    _rec_name = "activity_id"
    _description = "UnitActivity"

    activity_id = fields.Char(string="ID", copy=False, readonly=True)
    unit_reservation_id = fields.Many2one(comodel_name='unit.reservation', string="Reservation ID", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string="User", readonly=True)
    unit_details_id = fields.Many2one(comodel_name='unit.details', string="Unit", readonly=True)
    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', readonly=True)
    activity_date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    activity_type = fields.Selection([
        ('draft', 'Draft'),
        ('hold', 'Hold'),
        ('special_hold', 'Special Hold'),
        ('reserved', 'Tentatively Sold'),
        ('sold', 'Sold'),
        ('expired', 'Expired'),
        ('cancel', 'Cancel'),
        ('reset', 'Reset to Draft'),
    ], string='Activity Type', readonly=True)

    @api.model
    def create(self, vals):
        """Auto-generate sequential 5-digit activity ID if not provided."""
        if 'activity_id' not in vals or not vals['activity_id']:
            last_activity = self.search([], order='id desc', limit=1)
            if last_activity and last_activity.activity_id:
                next_id = int(last_activity.activity_id) + 1
            else:
                next_id = 1
            vals['activity_id'] = f"{next_id:05d}"
        return super(UnitActivity, self).create(vals)
