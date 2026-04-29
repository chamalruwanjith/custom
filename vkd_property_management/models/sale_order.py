# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Confirm sale order and update unit status to 'sold', complete reservations, and validate unit availability."""
        result = super(SaleOrder, self).action_confirm()

        allowed_statuses = ['available', 'hold', 'special_hold', 'reserved']

        for order in self:
            if order.origin:
                reservation = self.env['unit.reservation'].search([('reservation_id', '=', order.origin)], limit=1)
                if reservation:
                    reservation.write({
                        'reservation_status': 'sold',
                        'sold_date': fields.Date.today()
                    })
                    reservation._update_unit_status('sold')
                    reservation._update_unit_activity('sold')
                    reservation.action_notify_sale_agent()

                for line in order.order_line:
                    product = line.product_id
                    if product:
                        unit = self.env['unit.details'].search([('unit_code', '=', product.default_code)], limit=1)
                        if unit:
                            unit.write({
                                'unit_status': 'sold',
                                'is_unit_sold': True
                            })
            else:
                for line in order.order_line:
                    product = line.product_id
                    if product:
                        unit = self.env['unit.details'].search([('unit_code', '=', product.default_code)], limit=1)
                        if unit:
                            if unit.unit_status not in allowed_statuses:
                                raise ValidationError(_(
                                    "Unit %s is not available for sale. Current status: %s"
                                ) % (unit.unit_code, unit.unit_status))

                            unit.write({
                                'unit_status': 'sold',
                                'is_unit_sold': True
                            })
                            unit._update_unit_activity('sold')

        return result
