from odoo import _, api, fields, models


class Channel(models.Model):
    _inherit = 'discuss.channel'

    is_lead_notification_channel = fields.Boolean(default=False, string="Is Lead Notification Channel?")