from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Extend the sale order confirmation process to:
        1. Update unit status to 'sold' for related unit.
        2. Update the reservation_status of the related unit.reservation to 'sold'.
        """
        result = super(SaleOrder, self).action_confirm()

        for order in self:
            if order.origin:
                reservation = self.env['unit.reservation'].search([('reservation_id', '=', order.origin)], limit=1)
                if reservation:
                    reservation.write({'reservation_status': 'sold', 'sold_date': fields.Date.today()})
                    reservation._update_unit_status('sold')
                    reservation.action_notify_sale_agent()
                for line in order.order_line:
                    product = line.product_id
                    if product:
                        unit = self.env['unit.details'].search([('unit_code', '=', product.default_code)], limit=1)
                        if unit:
                            unit.write({'unit_status': 'sold', 'is_unit_sold': True})

        return result
