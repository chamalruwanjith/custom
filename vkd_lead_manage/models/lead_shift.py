from odoo import fields, models, api
from odoo.exceptions import ValidationError


class LeadShift(models.Model):
    _name = 'lead.shift'
    _description = 'Shift Configuration'
    _order = 'from_hour'

    name = fields.Char(string='Shift Name', required=True)
    from_hour = fields.Float(string='From', required=True, help='e.g. 8.5 = 08:30 AM')
    to_hour = fields.Float(string='To', required=True, help='e.g. 17.0 = 05:00 PM')
    next_day = fields.Boolean(
        string='Ends Next Day',
        help='Enable if this shift ends after midnight (e.g. 23:00 → 02:00 next day)',
    )
    active = fields.Boolean(default=True)

    @api.constrains('from_hour', 'to_hour', 'next_day')
    def _check_hours(self):
        for rec in self:
            if not (0 <= rec.from_hour < 24):
                raise ValidationError('From hour must be between 0 and 23:59.')
            if not (0 <= rec.to_hour < 24):
                raise ValidationError('To hour must be between 0 and 23:59.')
            if not rec.next_day and rec.to_hour <= rec.from_hour:
                raise ValidationError('To must be after From, or enable "Ends Next Day".')
