# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hold_expiration_days = fields.Integer(string='Hold Expiration Days')
    hold_unit_limit = fields.Integer(string='Hold Limit')

    @api.model
    def get_values(self):
        """Extend res.config.settings to add configuration fields for hold expiration days and hold unit limits."""
        res = super(ResConfigSettings, self).get_values()
        res.update(
            hold_expiration_days=int(self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_expiration_days')),
            hold_unit_limit=int(self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit')),
        )
        return res

    def set_values(self):
        """Save configuration values for hold expiration days and hold unit limit to system parameters."""
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('vkd_property_management.hold_expiration_days', self.hold_expiration_days)
        self.env['ir.config_parameter'].sudo().set_param('vkd_property_management.hold_unit_limit', self.hold_unit_limit)
