from odoo import fields, models


class LeadType(models.Model):
    _name = 'crm.lead.type'
    _description = 'Lead Type'
    _order = 'name'

    name = fields.Char(string='Type', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Lead type name must be unique.'),
    ]