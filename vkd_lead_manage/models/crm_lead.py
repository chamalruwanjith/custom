import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _order = "stage_id, create_date desc"

    attend_time = fields.Datetime(string='Attend Time', readonly=True, tracking=True, copy=False)
    response_time = fields.Float(string='Response Time (Minutes)', compute='_compute_response_time', store=True)
    attended_by = fields.Selection(
        [
            ('whatsapp', 'WhatsApp'),
            ('email', 'Email'),
            ('call', 'Call'),
            ('sms', 'SMS'),
        ],
        string="First Attended By",
        readonly=True,
        tracking=True,
        copy=False,
    )

    @api.model
    def update_attend_time(self, lead_id, first_attended_by):
        lead = self.browse(lead_id)
        if lead and not lead.attend_time:
            lead.attend_time = fields.Datetime.now()
            lead.attended_by = first_attended_by

            first_stage = self.env['crm.stage'].search([], order='sequence', limit=1)
            if lead.stage_id == first_stage:
                next_stage = self.env['crm.stage'].search(
                    [('sequence', '>', first_stage.sequence)], order='sequence', limit=1
                )
                if next_stage:
                    lead.stage_id = next_stage
            return True
        return False

    @api.depends('attend_time')
    def _compute_response_time(self):
        for lead in self:
            if lead.attend_time:
                create_date = fields.Datetime.from_string(lead.create_date)
                attend_time = fields.Datetime.from_string(lead.attend_time)

                # Get the difference in minutes
                time_difference = (attend_time - create_date).total_seconds() / 60.0
                lead.response_time = time_difference
            else:
                lead.response_time = 0.0

