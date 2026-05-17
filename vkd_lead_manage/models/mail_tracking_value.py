import pytz

from odoo import api, fields, models


class MailTrackingValue(models.Model):
    _inherit = 'mail.tracking.value'

    message_date = fields.Datetime(related='mail_message_id.date', string='Date')
    message_record_name = fields.Char(related='mail_message_id.record_name', string='Lead')
    message_author_id = fields.Many2one(
        'res.partner', related='mail_message_id.author_id', string='Changed By'
    )
    field_label = fields.Char(compute='_compute_field_label', string='Field Changed')
    crm_full_name = fields.Char(compute='_compute_crm_fields', string='Full Name')
    crm_stage_id = fields.Many2one('crm.stage', compute='_compute_crm_fields', string='Stage')
    crm_user_id = fields.Many2one('res.users', compute='_compute_crm_fields', string='Salesperson')

    @api.depends('field_id', 'field_info')
    def _compute_field_label(self):
        for rec in self:
            if rec.field_id:
                rec.field_label = rec.field_id.field_description
            elif rec.field_info:
                rec.field_label = rec.field_info.get('desc', '')
            else:
                rec.field_label = ''


    @api.depends('mail_message_id.res_id', 'mail_message_id.model')
    def _compute_crm_fields(self):
        for rec in self:
            if rec.mail_message_id.model == 'crm.lead' and rec.mail_message_id.res_id:
                lead = self.env['crm.lead'].browse(rec.mail_message_id.res_id)
                rec.crm_full_name = lead.full_name
                rec.crm_stage_id = lead.stage_id
                rec.crm_user_id = lead.user_id
            else:
                rec.crm_full_name = False
                rec.crm_stage_id = False
                rec.crm_user_id = False
