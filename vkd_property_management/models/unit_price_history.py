# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnitPriceHistory(models.Model):
    _name = "unit.price.history"
    _description = "Unit Price History"
    _order = "change_date desc"

    unit_details_id = fields.Many2one(comodel_name='unit.details', string="Unit", readonly=True, required=True)
    price_type = fields.Char(string="Price Type", readonly=True, help="Indicates if it's the Base Price or a Villa Multiple Price.")
    old_price = fields.Float(string="Previous Price", readonly=True)
    new_price = fields.Float(string="Updated Price", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string="User", readonly=True, default=lambda self: self.env.user)
    change_date = fields.Datetime(string="Date & Time", default=fields.Datetime.now, readonly=True)
