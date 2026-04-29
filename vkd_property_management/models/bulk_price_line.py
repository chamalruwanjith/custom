# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BulkPriceLine(models.Model):
    _name = "bulk.price.line"
    _rec_name = "bulk_amount"
    _description = "Bulk Price Line"

    currency_id = fields.Many2one(comodel_name='res.currency', string="Currency", required=True)
    create_date = fields.Datetime(string="Create Date", default=fields.Datetime.now, readonly=True)
    bulk_amount = fields.Float(string="Amount", required=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Created By", default=lambda self: self.env.user, readonly=True)
    bulk_line_status = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string="Status", readonly=True, default='draft')
    apartment_details_ids = fields.Many2many(comodel_name='apartment.details', string="Apartment")
