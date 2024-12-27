from datetime import datetime, timedelta
import pytz
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class LeadAllocate(models.Model):
    _name = 'lead.allocate'
    _inherit = 'mail.thread'
    _description = 'Lead Allocate'
    _rec_name = "team_id"

    team_id = fields.Many2one('crm.team', string='Team', tracking=True)
    user_id = fields.Many2one('res.users', string='Agent', tracking=True)
    shift_date = fields.Date(string='Shift Date', default=fields.Date.today, tracking=True)
    shift_type = fields.Selection(
        [('day', 'Day Shift'), ('night', 'Night Shift'), ('both', 'Both')], string="Shift Type", tracking=True)
    from_time = fields.Datetime(string='From', tracking=True)
    to_time = fields.Datetime(string='To', tracking=True)

    # @api.onchange('team_id')
    # def _onchange_team_id(self):
    #     """Update the user_id field's domain based on the selected team_id"""
    #     if self.team_id:
    #         user_ids = self.env['crm.team.member'].search([('crm_team_id', '=', self.team_id.id)]).mapped('user_id')
    #         return {'domain': {'user_id': [('id', 'in', user_ids.ids)]}}
    #     else:
    #         return {'domain': {'user_id': []}}

    @api.onchange('shift_type')
    def onchange_shift_type(self):
        if self.shift_date and self.shift_type:
            shift_date_dt = fields.Date.from_string(self.shift_date)

            ist_tz = pytz.timezone('Asia/Colombo')

            if self.shift_type == 'day':
                # Day Shift: From 8:00 AM to 5:00 PM
                from_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(hours=8)).astimezone(pytz.utc)
                to_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(hours=17)).astimezone(pytz.utc)
                self.from_time = fields.Datetime.to_string(from_time_utc)
                self.to_time = fields.Datetime.to_string(to_time_utc)
            elif self.shift_type == 'night':
                # Night Shift: From 5:00 PM to 8:00 AM the next day
                from_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(hours=17)).astimezone(pytz.utc)
                to_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(days=1, hours=8)).astimezone(
                    pytz.utc)
                self.from_time = fields.Datetime.to_string(from_time_utc)
                self.to_time = fields.Datetime.to_string(to_time_utc)
            elif self.shift_type == 'both':
                # Both Shifts: From 8:00 AM to 8:00 AM the next day
                from_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(hours=8)).astimezone(pytz.utc)
                to_time_utc = ist_tz.localize(
                    datetime.combine(shift_date_dt, datetime.min.time()) + timedelta(days=1, hours=8)).astimezone(
                    pytz.utc)
                self.from_time = fields.Datetime.to_string(from_time_utc)
                self.to_time = fields.Datetime.to_string(to_time_utc)

    @api.constrains('from_time', 'to_time')
    def _check_time_overlap(self):
        for record in self:
            if record.from_time and record.to_time:
                overlapping_shifts = self.search([
                    ('team_id', '=', record.team_id.id),
                    ('shift_date', '=', record.shift_date),
                    ('id', '!=', record.id),
                    ('from_time', '<', record.to_time),
                    ('to_time', '>', record.from_time)
                ])
                if overlapping_shifts:
                    raise ValidationError('The selected time slot is already taken.')