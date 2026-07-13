from odoo import fields, models


class LeadProject(models.Model):
    _name = 'crm.lead.project'
    _description = 'Lead Project'
    _order = 'name'

    name = fields.Char(string='Project', required=True, help='Project name matched against the ad set name, e.g. BAYFONTE, PORT CITY.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Project name must be unique.'),
    ]