import logging
import re
import traceback
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_REGION_TOKENS = {
    'ASIA': 'asia',
    'LOCAL': 'asia',  # LOCAL = Sri Lanka = Asia
    'OCEANIA': 'oceania',
    'EUROPE': 'europe',
    'AFRICA': 'africa',
    'NORTH AMERICA': 'north_america',
    'SOUTH AMERICA': 'south_america',
    'ANTARCTICA': 'antarctica',
}


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
    best_contact_time = fields.Char(string='Best Contact Time')
    desired_number_of_perches = fields.Char(string='Desired Number of Perches')
    job_title = fields.Char(string='Job Title')

    lead_allocate_id = fields.Many2one('lead.allocate', string='Lead Allocate')

    project_id = fields.Many2one('apartment.details', string='Project', readonly=True)
    lead_type_id = fields.Many2one('crm.lead.type', string='Lead Type', readonly=True)
    source_region = fields.Selection([
        ('asia', 'Asia'),
        ('oceania', 'Oceania'),
        ('europe', 'Europe'),
        ('africa', 'Africa'),
        ('north_america', 'North America'),
        ('south_america', 'South America'),
        ('antarctica', 'Antarctica'),
    ], string='Source Region', readonly=True)
    digital_team_id = fields.Many2one('crm.team', string='Digital Team', readonly=True)

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
                # ads_management + ads_read required; fall back to ID when name is absent (organic lead or missing scope)
                'name': lead.get('ad_name') or ad_id,
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
                # ads_management + ads_read required; fall back to ID when name is absent
                'name': lead.get('adset_name') or adset_id,
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
                # ads_management + ads_read required; fall back to ID when name is absent
                'name': lead.get('campaign_name') or campaign_id,
            })
        campaign_cache[campaign_id] = campaign.id
        return campaign.id

    def _parse_adset_name(self, adset_name):
        """
        Parse project, lead type, source country, and digital team from the adset name.

        Naming convention (segments delimited by ' - '):
            {PROJECT} - {COUNTRY} - {TYPE} - {D0X} - {DATE}
        Example: PORT CITY - LOCAL - LEAD - D01 - 19/MAY

        Recognition order:
          1. Digital team — token matching D0*\\d+  (D01, D02, D001, D002)
          2. Region       — token matched against _REGION_TOKENS (Asia, Europe, North America …)
          3. Lead type    — WB if token present, otherwise defaults to NC
          4. Project      — substring match on apartment.details.apartment_name
                            to handle names like "STANFORD AVENUE - MALABE" vs token "STANFORD AVENUE"
        """
        if not adset_name:
            return {}

        result = {}
        tokens = [t.strip() for t in adset_name.split(' - ') if t.strip()]
        # Remove date tokens like "19/MAY" or "01/JAN"
        tokens = [t for t in tokens if not re.match(r'^\d{1,2}/[A-Za-z]+$', t)]
        unmatched = list(tokens)

        # 1. Digital team — D01 / D02 / D001 / D002.
        #    Accept the code both as a standalone ' - ' token (documented convention,
        #    e.g. "... - D01 - ...") and embedded in a space-delimited name with no
        #    ' - ' separators (e.g. "D02 Crest Leads May Wk 3-4").
        team_token = next((t for t in unmatched if re.match(r'^D0*\d+$', t, re.IGNORECASE)), None)
        if not team_token:
            m = re.search(r'\bD0*\d+\b', adset_name, re.IGNORECASE)
            team_token = m.group(0) if m else None
        if team_token:
            team = self.env['crm.team'].search([('name', 'ilike', team_token)], limit=1)
            if team:
                result['digital_team_id'] = team.id
            # Drop any token that contains the code so it isn't re-used below
            # (e.g. mistaken for a project name).
            unmatched[:] = [t for t in unmatched if team_token not in t]

        # 2. Region — match token against the fixed region map
        for token in list(unmatched):
            region_key = _REGION_TOKENS.get(token.upper())
            if region_key:
                result['source_region'] = region_key
                unmatched.remove(token)
                break

        # 3. Lead type — only two values exist: WB and NC.
        #    If "WB" token is present use it; otherwise default to NC.
        wb_token = next((t for t in unmatched if t.upper() == 'WB'), None)
        if wb_token:
            lead_type = self.env['crm.lead.type'].search([('name', '=ilike', 'WB')], limit=1)
            if lead_type:
                result['lead_type_id'] = lead_type.id
            unmatched.remove(wb_token)
        else:
            lead_type = self.env['crm.lead.type'].search([('name', '=ilike', 'NC')], limit=1)
            if lead_type:
                result['lead_type_id'] = lead_type.id

        # 4. Project — substring match so "STANFORD AVENUE" hits "STANFORD AVENUE - MALABE"
        for token in list(unmatched):
            project = self.env['apartment.details'].search([('apartment_name', 'ilike', token)], limit=1)
            if project:
                result['project_id'] = project.id
                unmatched.remove(token)
                break

        if unmatched:
            _logger.debug('Adset "%s": unmatched tokens %s', adset_name, unmatched)

        return result

    # Whole-word "land" / "lands", case-insensitive, so "Highland", "England",
    # "mainland" etc. do not falsely route to the Lands allocation.
    _LANDS_ADSET_RE = re.compile(r'\blands?\b', re.IGNORECASE)

    def _allocation_type_for_adset(self, adset_name):
        return 'lands' if adset_name and self._LANDS_ADSET_RE.search(adset_name) else 'apartment'

    def _find_lead_allocate(self, lead_create_time, form, adset_name=''):
        domain = [
            ('from_time', '<=', lead_create_time),
            ('to_time', '>=', lead_create_time),
        ]
        if form.team_id:
            domain += ['|', ('team_id', '=', form.team_id.id), ('team_id', '=', False)]
        company_id = form.page_id.company_id.id if form.page_id and form.page_id.company_id else False
        if company_id:
            domain += ['|', ('company_id', '=', company_id), ('company_id', '=', False)]

        Allocate = self.env['lead.allocate'].sudo()
        alloc_type = self._allocation_type_for_adset(adset_name)
        # Prefer an allocation matching the lead's type (Lands vs Apartment),
        # then fall back to any allocation so the lead is still assigned.
        allocate = Allocate.search(
            domain + [('allocation_type', '=', alloc_type)], limit=1, order='from_time desc')
        if not allocate:
            allocate = Allocate.search(domain, limit=1, order='from_time desc')
        return allocate

    def prepare_lead_creation(self, lead, form, ad_cache, adset_cache, campaign_cache):
        vals, notes = self.get_fields_from_data(lead, form)
        lead_create_time = lead['created_time'].split('+')[0].replace('T', ' ')
        lead_allocate = self._find_lead_allocate(lead_create_time, form, lead.get('adset_name', ''))

        assigned_user = None
        if lead_allocate:
            assigned_user = lead_allocate.get_next_user()

        # Parse project / country / lead type / digital team from the adset name;
        # fall back to form-level defaults when a token is absent or unrecognised
        parsed = self._parse_adset_name(lead.get('adset_name', ''))

        vals.update({
            'facebook_lead_id': lead['id'],
            'facebook_is_organic': lead.get('is_organic', False),
            'name': self.get_opportunity_name(vals, lead, form),
            'description': "\n".join(notes),
            'team_id': form.team_id.id if form.team_id else None,
            'company_id': form.page_id.company_id.id if form.page_id and form.page_id.company_id else None,
            'campaign_id': form.campaign_id.id or self.get_campaign(lead, campaign_cache),
            'source_id': form.source_id.id if form.source_id else None,
            'medium_id': form.medium_id.id or self.get_ad(lead, ad_cache),
            'user_id': assigned_user.id if assigned_user else None,
            'facebook_adset_id': self.get_adset(lead, adset_cache),
            'adset_name': lead.get('adset_name', ''),
            'facebook_form_id': form.id,
            'facebook_date_create': lead['created_time'].split('+')[0].replace('T', ' '),
            'lead_allocate_id': lead_allocate.id if lead_allocate else None,
            'project_id': parsed.get('project_id') or form.project_id.id or None,
            'lead_type_id': parsed.get('lead_type_id') or form.lead_type_id.id or None,
            'source_region': parsed.get('source_region'),
            'digital_team_id': parsed.get('digital_team_id') or form.digital_team_id.id or None,
        })
        return vals

    def lead_creation(self, lead, form, ad_cache, adset_cache, campaign_cache):
        vals = self.prepare_lead_creation(lead, form, ad_cache, adset_cache, campaign_cache)
        return self.create(vals)

    def get_opportunity_name(self, vals, lead, form):
        if not vals.get('name'):
            vals['name'] = '%s' % (form.name)
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

        # Per-page caches — evicted on savepoint failure to avoid stale IDs
        ad_cache = {}
        adset_cache = {}
        campaign_cache = {}
        form_campaign_id = None
        form_medium_id = None

        for lead_raw in r['data']:
            lead_id = lead_raw.get('id', 'unknown')
            lead = None
            # Snapshot cache key sets so we can evict rolled-back entries on failure
            ad_keys_before = set(ad_cache)
            adset_keys_before = set(adset_cache)
            campaign_keys_before = set(campaign_cache)

            try:
                with self.env.cr.savepoint():
                    lead = self.process_lead_field_data(lead_raw)
                    if self.search(
                        [('facebook_lead_id', '=', lead.get('id')), '|', ('active', '=', True), ('active', '=', False)],
                        limit=1,
                    ):
                        continue
                    vals = self.prepare_lead_creation(lead, form, ad_cache, adset_cache, campaign_cache)
                    self.create(vals)
            except Exception:
                _logger.exception(
                    'Failed to process lead %s in form %s (form_id=%s, company=%s)',
                    lead_id, form.name, form.facebook_form_id, form.company_id.name or 'N/A',
                )
                # Evict cache entries added during this failed savepoint — they point to rolled-back rows
                for k in set(ad_cache) - ad_keys_before:
                    del ad_cache[k]
                for k in set(adset_cache) - adset_keys_before:
                    del adset_cache[k]
                for k in set(campaign_cache) - campaign_keys_before:
                    del campaign_cache[k]
                try:
                    data = lead or lead_raw or {}
                    self.env['crm.facebook.lead.error'].sudo().create({
                        'facebook_lead_id': lead_id,
                        'form_id': form.id,
                        'adset_name': data.get('adset_name') or '',
                        'error': traceback.format_exc(),
                        'lead_data': str(data),
                    })
                except Exception:
                    _logger.exception('Could not save error record for lead %s', lead_id)
                continue

            # Auto-populate outside the savepoint so a failure here cannot roll back
            # the already-committed lead record
            if lead is not None:
                try:
                    if form_campaign_id is None and lead.get('campaign_id'):
                        form_campaign_id = self.get_campaign(lead, campaign_cache)
                    if form_medium_id is None and lead.get('ad_id'):
                        form_medium_id = self.get_ad(lead, ad_cache)
                except Exception:
                    _logger.exception(
                        'Failed to resolve campaign/ad for auto-populate on lead %s, form %s',
                        lead_id, form.name,
                    )

        form_updates = {}
        if not form.campaign_id and form_campaign_id:
            form_updates['campaign_id'] = form_campaign_id
        if not form.medium_id and form_medium_id:
            form_updates['medium_id'] = form_medium_id
        if form_updates:
            try:
                form.sudo().write(form_updates)
            except Exception:
                _logger.exception('Failed to update campaign/medium on form %s', form.name)

        if r.get('paging') and r['paging'].get('next'):
            _logger.info('Fetching next page for form %s', form.name)
            try:
                next_r = requests.get(r['paging']['next'], timeout=30).json()
            except requests.RequestException:
                _logger.exception('Network error fetching next page for form %s', form.name)
                return
            except ValueError:
                _logger.exception('Invalid JSON in next-page response for form %s', form.name)
                return
            self.lead_processing(next_r, form)

        try:
            self.env.cr.commit()
        except Exception:
            _logger.exception('Failed to commit after processing page for form %s', form.name)
            self.env.cr.rollback()

    @api.model
    def get_facebook_leads(self):
        fb_api = "https://graph.facebook.com/v21.0/"
        for form in self.env['crm.facebook.form'].sudo().search([]):
            form_status = self.get_form_status(form.facebook_form_id, form.access_token)
            if form_status != 'ACTIVE':
                _logger.info('Form %s is not active, skipping lead fetch.' % form.name)
                continue
            else:
                form.status = True

            _logger.info('Starting to fetch leads from Form: %s (Company: %s)' % (form.name, form.company_id.name or 'N/A'))
            params = {'access_token': form.access_token,
                      'fields': 'created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,is_organic,status'
                      }
            if form.date_retrieval:
                params.update({
                    'filtering': "[{'field': 'time_created', 'operator': 'GREATER_THAN', 'value': %s}]" % (
                        int(form.date_retrieval.timestamp())),
                })
            r = requests.get(fb_api + form.facebook_form_id + "/leads", params=params).json()
            _logger.info(
                'Lead payload for form %s — first lead keys: %s',
                form.name,
                list(r['data'][0].keys()) if r.get('data') else r.get('error', '(empty response)'),
            )
            if r.get('error'):
                _logger.error('Facebook API error for form %s: %s' % (form.name, r['error']['message']))
                continue
            # Use form's company context so company-specific defaults apply to created leads
            lead_env = self.sudo().with_company(form.company_id) if form.company_id else self.sudo()
            lead_env.lead_processing(r, form)
            form.date_retrieval = fields.Datetime.now()
        _logger.info('Fetch of leads has ended')

    def get_form_status(self, form_id, access_token):
        fb_api = "https://graph.facebook.com/v21.0/"
        params = {
            'access_token': access_token,
            'fields': 'status'
        }
        url = f"{fb_api}{form_id}"
        response = requests.get(url, params=params).json()

        if response.get('error'):
            raise UserError(response['error']['message'])

        return response.get('status')
