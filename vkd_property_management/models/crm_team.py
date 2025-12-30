from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "crm.team"

    is_enabled_portal = fields.Boolean(string="Is Enabled Portal?")
