# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _


class SaleCustomerSelect(models.TransientModel):
    _name = 'sale.customer.select'
    _description = 'Sale Customer Select'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                 help="Select the customer for the Sale Order")
    unit_details_id = fields.Many2one('unit.details', string='Unit', required=True)

    def action_create_sale_order(self):
        """Creates the sale order based on the selected customer."""
        self.ensure_one()
        unit = self.unit_details_id
        product = self.env['product.product'].search([('default_code', '=', unit.unit_code)], limit=1)

        if not product:
            raise exceptions.UserError(_('No product found for this unit. Please ensure the product is created.'))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': product.lst_price,
            })]
        })

        unit.write({'unit_status': 'reserved'})

        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
        }
