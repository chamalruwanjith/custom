from odoo import fields, models


class LeadBranch(models.Model):
    _name = 'crm.lead.branch'
    _description = 'Lead Branch'
    _order = 'name'

    name = fields.Char(string='Branch Code', required=True, help='Code matched against the ad set name, e.g. CMB, GLE, KRN, NGM.')
    description = fields.Char(string='Description', help='Full branch name, e.g. Colombo, Galle.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Branch code must be unique.'),
    ]