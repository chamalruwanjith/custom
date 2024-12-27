import requests

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CrmFacebookPage(models.Model):
    _name = 'crm.facebook.page'
    _description = 'Facebook Page'

    label = fields.Char(string='Page Label')
    # TODO: rename to id
    name = fields.Char(required=True, string='Page ID')
    access_token = fields.Char(required=True, string='Page Access Token')
    form_ids = fields.One2many('crm.facebook.form', 'page_id', string='Lead Forms')
    company_id = fields.Many2one('res.company', string='Company')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'You cannot create a Page twice')
    ]

    @api.depends('label', 'name')
    def name_get(self):
        result = []
        for page in self:
            name = page.label if page.label else page.name
            result.append((page.id, name))
        return result

    def form_processing(self, r):
        if not r.get('data'):
            return
        for form in r['data']:
            if self.form_ids.filtered(
                    lambda f: f.facebook_form_id == form['id']):
                continue
            if form['status'] == 'ACTIVE':
                self.env['crm.facebook.form'].create({
                    'name': form['name'],
                    'facebook_form_id': form['id'],
                    'page_id': self.id,
                    'company_id': self.company_id.id
                }).get_fields()

        if r.get('paging') and r['paging'].get('next'):
            self.form_processing(requests.get(r['paging']['next']).json())
        return

    def get_forms(self):
        r = requests.get("https://graph.facebook.com/v7.0/" + self.name + "/leadgen_forms",
                         params={'access_token': self.access_token}).json()
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        self.form_processing(r)
