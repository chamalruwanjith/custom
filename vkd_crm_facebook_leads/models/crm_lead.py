import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    facebook_lead_id = fields.Char(string='Facebook Lead', readonly=True)
    facebook_page_id = fields.Many2one(
        'crm.facebook.page', related='facebook_form_id.page_id',
        store=True, readonly=True, string='Facebook Page')
    facebook_form_id = fields.Many2one('crm.facebook.form', readonly=True, string='Facebook Form')
    facebook_adset_id = fields.Many2one('utm.adset', readonly=True, string='Facebook Adset')
    facebook_ad_id = fields.Many2one(
        'utm.medium', related='medium_id', store=True, readonly=True,
        string='Facebook Ad')
    facebook_campaign_id = fields.Many2one(
        'utm.campaign', related='campaign_id', store=True, readonly=True,
        string='Facebook Campaign')
    facebook_date_create = fields.Datetime(readonly=True, string='Facebook Date Create')
    facebook_is_organic = fields.Boolean(readonly=True, string='Facebook Is Organic')

    lead_id = fields.Char(string='Lead')
    purpose = fields.Char(string='Purpose ')
    adset_name = fields.Char(string='Adset Name')
    property_type = fields.Selection(string='Property Type ', selection=[('apartment', 'Apartment'), ('villa', 'Villa')])
    budget = fields.Float(string='Budget ')
    full_name = fields.Char(string='Full Name')
    email_address = fields.Char(string='Email')
    contact_number = fields.Char(string='Contact Number')
    additional_phone_number = fields.Char(string='Additional Phone Number')
    whatsapp_number = fields.Char(string='WhatsApp Number')
    best_contact_time = fields.Datetime(string='Best Contact Time')
    desired_number_of_perches = fields.Char(string='Desired Number of Perches')
    job_title = fields.Char(string='Job Title')

    lead_allocate_id = fields.Many2one('lead.allocate', string='Lead Allocate')


    _sql_constraints = [
        ('facebook_lead_unique', 'unique(facebook_lead_id)',
         'This Facebook lead already exists!')
    ]

    def get_ad(self, lead, ad_cache):
        ad_id = lead.get('ad_id')
        if not ad_id:
            return None

        if ad_id in ad_cache:
            return ad_cache[ad_id]

        ad = self.env['utm.medium'].search([('facebook_ad_id', '=', ad_id)], limit=1)
        if not ad:
            ad = self.env['utm.medium'].create({
                'facebook_ad_id': ad_id,
                'name': lead['ad_name'],
            })
        ad_cache[ad_id] = ad.id
        return ad.id

    def get_adset(self, lead, adset_cache):
        adset_id = lead.get('adset_id')
        if not adset_id:
            return None

        if adset_id in adset_cache:
            return adset_cache[adset_id]

        adset = self.env['utm.adset'].search([('facebook_adset_id', '=', adset_id)], limit=1)
        if not adset:
            adset = self.env['utm.adset'].create({
                'facebook_adset_id': adset_id,
                'name': lead['adset_name'],
            })
        adset_cache[adset_id] = adset.id
        return adset.id

    def get_campaign(self, lead, campaign_cache):
        campaign_id = lead.get('campaign_id')
        if not campaign_id:
            return None

        if campaign_id in campaign_cache:
            return campaign_cache[campaign_id]

        campaign = self.env['utm.campaign'].search([('facebook_campaign_id', '=', campaign_id)], limit=1)
        if not campaign:
            campaign = self.env['utm.campaign'].create({
                'facebook_campaign_id': campaign_id,
                'name': lead['campaign_name'],
            })
        campaign_cache[campaign_id] = campaign.id
        return campaign.id

    def prepare_lead_creation(self, lead, form, ad_cache, adset_cache, campaign_cache):
        vals, notes = self.get_fields_from_data(lead, form)
        lead_create_time = lead['created_time'].split('+')[0].replace('T', ' ')
        lead_allocate = self.env['lead.allocate'].search([
            ('from_time', '<=', lead_create_time),
            ('to_time', '>=', lead_create_time),
        ], limit=1, order='from_time desc')

        vals.update({
            'facebook_lead_id': lead['id'],
            'facebook_is_organic': lead['is_organic'],
            'name': self.get_opportunity_name(vals, lead, form),
            'description': "\n".join(notes),
            'team_id': form.team_id.id if form.team_id else None,
            'company_id': form.page_id.company_id.id if form.page_id and form.page_id.company_id else None,
            'campaign_id': form.campaign_id.id or self.get_campaign(lead, campaign_cache),
            'source_id': form.source_id.id if form.source_id else None,
            'medium_id': form.medium_id.id or self.get_ad(lead, ad_cache),
            # 'user_id': form.team_id.user_id.id if form.team_id and form.team_id.user_id else None,
            'user_id': lead_allocate.user_id.id if lead_allocate.user_id else None,
            'facebook_adset_id': self.get_adset(lead, adset_cache),
            'facebook_form_id': form.id,
            'facebook_date_create': lead['created_time'].split('+')[0].replace('T', ' '),
            'lead_allocate_id': lead_allocate.id if lead_allocate else None,
        })
        return vals

    def lead_creation(self, lead, form, ad_cache, adset_cache, campaign_cache):
        vals = self.prepare_lead_creation(lead, form, ad_cache, adset_cache, campaign_cache)
        return self.create(vals)

    def get_opportunity_name(self, vals, lead, form):
        if not vals.get('name'):
            vals['name'] = '%s - %s' % (form.name, lead['id'])
        return vals['name']

    def get_fields_from_data(self, lead, form):
        vals, notes = {}, []
        form_mapping = form.fields_mapping_ids.filtered(lambda m: m.odoo_field_id).mapped('facebook_field')
        unmapped_fields = []
        for name, value in lead.items():
            if name not in form_mapping:
                unmapped_fields.append((name, value))
                continue
            odoo_field_id = form.fields_mapping_ids.filtered(lambda m: m.facebook_field == name).odoo_field_id
            notes.append('%s: %s' % (odoo_field_id.field_description, value))
            if odoo_field_id.ttype == 'many2one':
                related_value = self.env[odoo_field_id.relation].search([('display_name', '=', value)])
                vals.update({odoo_field_id.name: related_value.id if related_value else None})
            elif odoo_field_id.ttype in ('float', 'monetary'):
                try:
                    vals.update({odoo_field_id.name: float(value)})
                except (ValueError, TypeError):
                    _logger.warning('Cannot convert "%s" to float for field %s, storing in notes only', value, odoo_field_id.name)
            elif odoo_field_id.ttype == 'integer':
                try:
                    vals.update({odoo_field_id.name: int(value)})
                except (ValueError, TypeError):
                    _logger.warning('Cannot convert "%s" to int for field %s, storing in notes only', value, odoo_field_id.name)
            elif odoo_field_id.ttype in ('date', 'datetime'):
                vals.update({odoo_field_id.name: value.split('+')[0].replace('T', ' ')})
            elif odoo_field_id.ttype == 'selection':
                vals.update({odoo_field_id.name: value})
            elif odoo_field_id.ttype == 'boolean':
                vals.update({odoo_field_id.name: value == 'true' if value else False})
            else:
                vals.update({odoo_field_id.name: value})

        for name, value in unmapped_fields:
            notes.append('%s: %s' % (name, value))

        return vals, notes

    def process_lead_field_data(self, lead):
        field_data = lead.pop('field_data')
        lead_data = dict(lead)
        lead_data.update({l['name']: l['values'][0] for l in field_data if l.get('name') and l.get('values')})
        return lead_data

    def lead_processing(self, r, form):
        if not r.get('data'):
            return

        # Caching to avoid repeated database queries
        ad_cache = {}
        adset_cache = {}
        campaign_cache = {}

        leads_to_create = []
        for lead in r['data']:
            lead = self.process_lead_field_data(lead)
            if not self.search(
                    [('facebook_lead_id', '=', lead.get('id')), '|', ('active', '=', True), ('active', '=', False)],
                    limit=1):
                leads_to_create.append(self.prepare_lead_creation(lead, form, ad_cache, adset_cache, campaign_cache))

        if leads_to_create:
            self.create(leads_to_create)

        if r.get('paging') and r['paging'].get('next'):
            _logger.info('Fetching a new page in Form: %s' % form.name)
            self.lead_processing(requests.get(r['paging']['next']).json(), form)

        try:
            self.env.cr.commit()
        except Exception:
            self.env.cr.rollback()
        return

    @api.model
    def get_facebook_leads(self):
        fb_api = "https://graph.facebook.com/v19.0/"
        for form in self.env['crm.facebook.form'].search([]):
            form_status = self.get_form_status(form.facebook_form_id, form.access_token)
            if form_status != 'ACTIVE':
                _logger.info('Form %s is not active, skipping lead fetch.' % form.name)
                continue
            else:
                form.status = True

            # /!\ NOTE: We have to try lead creation if it fails we just log it into the Lead Form?
            _logger.info('Starting to fetch leads from Form: %s' % form.name)
            params = {'access_token': form.access_token,
                      'fields': 'created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,is_organic,status'
                      }
            if form.date_retrieval:
                params.update({
                    'filtering': "[{'field': 'time_created', 'operator': 'GREATER_THAN', 'value': %s}]" % (
                        int(form.date_retrieval.timestamp())),
                })
            r = requests.get(fb_api + form.facebook_form_id + "/leads", params=params).json()
            if r.get('error'):
                raise UserError(r['error']['message'])
            self.lead_processing(r, form)
            # Update the date_retrieval field after successful fetching
            form.date_retrieval = fields.Datetime.now()
        _logger.info('Fetch of leads has ended')

    def get_form_status(self, form_id, access_token):
        fb_api = "https://graph.facebook.com/v19.0/"
        params = {
            'access_token': access_token,
            'fields': 'status'
        }
        url = f"{fb_api}{form_id}"
        response = requests.get(url, params=params).json()

        if response.get('error'):
            raise UserError(response['error']['message'])

        return response.get('status')
