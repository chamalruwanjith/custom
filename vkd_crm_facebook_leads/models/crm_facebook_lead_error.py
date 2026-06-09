from odoo import models, fields


class CrmFacebookLeadError(models.Model):
    _name = 'crm.facebook.lead.error'
    _description = 'Facebook Lead Import Error'
    _order = 'create_date desc'
    _rec_name = 'facebook_lead_id'

    facebook_lead_id = fields.Char(string='Facebook Lead ID', readonly=True)
    form_id = fields.Many2one('crm.facebook.form', string='Form', readonly=True, ondelete='set null')
    adset_name = fields.Char(string='Adset Name', readonly=True)
    error = fields.Text(string='Error', readonly=True)
    lead_data = fields.Text(string='Lead Data', readonly=True)
