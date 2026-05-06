from datetime import datetime, timedelta
import pytz
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class LeadAllocateLine(models.Model):
    _name = 'lead.allocate.line'
    _description = 'Lead Allocate Agent Line'
    _order = 'sequence, id'

    allocate_id = fields.Many2one('lead.allocate', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Agent', required=True)
    sequence = fields.Integer(string='Order', default=10)
    lead_count = fields.Integer(string='Leads Received', default=0, readonly=True)

