# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "crm.team"

    is_enabled_portal = fields.Boolean(string="Is Enabled Portal?")
