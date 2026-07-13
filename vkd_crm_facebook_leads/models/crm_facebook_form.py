import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CrmFacebookForm(models.Model):
    _name = 'crm.facebook.form'
    _description = 'Facebook Form Page'

    name = fields.Char(string='Name', required=True)
    facebook_form_id = fields.Char(required=True, string='Form ID')
    access_token = fields.Char(required=True, related='page_id.access_token', string='Page Access Token')
    page_id = fields.Many2one('crm.facebook.page', readonly=True, ondelete='cascade', string='Facebook Page')
    fields_mapping_ids = fields.One2many('crm.facebook.form.field', 'form_id', string='Fields Mapping')
    team_id = fields.Many2one('crm.team', domain=['|', ('use_leads', '=', True), ('use_opportunities', '=', True)],
                              string="Sales Team")
    campaign_id = fields.Many2one('utm.campaign', string='Campaign')
    source_id = fields.Many2one('utm.source', string='Source')
    medium_id = fields.Many2one('utm.medium', string='Medium')
    date_retrieval = fields.Datetime(string='Fetch Leads After')
    status = fields.Boolean(string='Active', default=False)
    company_id = fields.Many2one('res.company', required=True, string='Company')

    project_id = fields.Many2one('crm.lead.project', string='Project')
    lead_type_id = fields.Many2one('crm.lead.type', string='Lead Type')
    country_id = fields.Many2one('res.country', string='Country')
    digital_team_id = fields.Many2one('crm.team', string='Digital Team')

    def get_fields(self):
        self.fields_mapping_ids.unlink()
        r = requests.get("https://graph.facebook.com/v21.0/" + self.facebook_form_id,
                         params={'access_token': self.access_token, 'fields': 'questions'}).json()
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        if r.get('questions'):
            for question in r.get('questions'):
                self.env['crm.facebook.form.field'].create({
                    'form_id': self.id,
                    'name': question['label'],
                    'facebook_field': question['key'],
                    'odoo_field_id': self.env['crm.facebook.form.mapping'].search(
                        [('facebook_field', '=', question['key'])], limit=1) and self.env[
                                      'crm.facebook.form.mapping'].search([('facebook_field', '=', question['key'])],
                                                                          limit=1).odoo_field_id.id or ''
                })

    def action_guess_mapping(self):
        for rec in self:
            rec.fields_mapping_ids.action_guess_mapping()
