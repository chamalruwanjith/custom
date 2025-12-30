from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_number = fields.Char(string="WhatsApp Number")
