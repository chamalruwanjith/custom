from datetime import datetime, timedelta
import pytz
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class LeadAllocate(models.Model):
    _name = 'lead.allocate'
    _inherit = 'mail.thread'
    _description = 'Lead Allocate'
    _rec_name = 'display_name'

    team_id = fields.Many2one('crm.team', string='Team', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    distribution_type = fields.Selection(
        [('single', 'Single Agent (Lands)'), ('round_robin', 'Round Robin (Skyline)')],
        string='Distribution Type', default='single', required=True, tracking=True,
    )

    user_id = fields.Many2one('res.users', string='Agent', tracking=True)
    allocate_line_ids = fields.One2many('lead.allocate.line', 'allocate_id', string='Agents')
    next_user_index = fields.Integer(string='Next Agent Index', default=0, copy=False)

    shift_date = fields.Date(string='Shift Date', default=fields.Date.today, required=True, tracking=True)
    shift_id = fields.Many2one('lead.shift', string='Shift', required=True, tracking=True)
    from_time = fields.Datetime(string='From', compute='_compute_shift_times', store=True, readonly=True, tracking=True)
    to_time = fields.Datetime(string='To', compute='_compute_shift_times', store=True, readonly=True, tracking=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('team_id', 'shift_id', 'shift_date')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.team_id:
                parts.append(rec.team_id.name)
            if rec.shift_id:
                parts.append(rec.shift_id.name)
            if rec.shift_date:
                parts.append(str(rec.shift_date))
            rec.display_name = ' / '.join(parts) if parts else '/'

    @api.depends('shift_id', 'shift_date')
    def _compute_shift_times(self):
        ist_tz = pytz.timezone('Asia/Colombo')
        for rec in self:
            if not (rec.shift_id and rec.shift_date):
                rec.from_time = False
                rec.to_time = False
                continue
            from_h = int(rec.shift_id.from_hour)
            from_m = round((rec.shift_id.from_hour - from_h) * 60)
            to_h = int(rec.shift_id.to_hour)
            to_m = round((rec.shift_id.to_hour - to_h) * 60)
            from_dt = ist_tz.localize(
                datetime.combine(rec.shift_date, datetime.min.time()) + timedelta(hours=from_h, minutes=from_m))
            to_base = rec.shift_date + timedelta(days=1) if rec.shift_id.next_day else rec.shift_date
            to_dt = ist_tz.localize(
                datetime.combine(to_base, datetime.min.time()) + timedelta(hours=to_h, minutes=to_m))
            rec.from_time = from_dt.astimezone(pytz.utc).replace(tzinfo=None)
            rec.to_time = to_dt.astimezone(pytz.utc).replace(tzinfo=None)

    @api.constrains('distribution_type', 'user_id', 'allocate_line_ids')
    def _check_agents(self):
        for rec in self:
            if rec.distribution_type == 'single' and not rec.user_id:
                raise ValidationError('Single Agent mode requires an Agent to be set.')
            if rec.distribution_type == 'round_robin':
                if not rec.allocate_line_ids:
                    raise ValidationError('Round Robin mode requires at least one agent in the Agents list.')
                if len(rec.allocate_line_ids) > 5:
                    raise ValidationError('Round Robin mode allows a maximum of 5 agents per shift.')

    def _overlap_extra_domain(self):
        """Extra domain leaves that further scope what counts as a conflicting
        overlap. Returns [] by default, so any two allocations for the same team
        with overlapping times clash. Sub-modules may override to allow several
        parallel allocations in the same slot (e.g. one per Facebook page)."""
        self.ensure_one()
        return []

    @api.constrains('from_time', 'to_time', 'team_id')
    def _check_time_overlap(self):
        for record in self:
            if record.from_time and record.to_time:
                overlapping = self.search([
                    ('team_id', '=', record.team_id.id),
                    ('id', '!=', record.id),
                    ('from_time', '<', record.to_time),
                    ('to_time', '>', record.from_time),
                ] + record._overlap_extra_domain())
                if overlapping:
                    raise ValidationError(
                        'The time slot overlaps with an existing allocation for team "%s".' % record.team_id.name
                    )

    def get_next_user(self):
        self.ensure_one()
        if self.distribution_type == 'single':
            return self.user_id

        lines = self.allocate_line_ids.sorted('sequence')
        if not lines:
            return self.env['res.users']

        idx = self.next_user_index % len(lines)
        user = lines[idx].user_id
        lines[idx].lead_count += 1
        self.next_user_index = (idx + 1) % len(lines)
        return user

    def reset_lead_counts(self):
        for rec in self:
            rec.next_user_index = 0
            rec.allocate_line_ids.write({'lead_count': 0})
