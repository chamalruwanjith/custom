import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmFacebookFormMapping(models.Model):
    _name = 'crm.facebook.form.mapping'
    _description = 'Default field mapping for new forms'

    odoo_field_id = fields.Many2one('ir.model.fields',
                                 domain=[('model', '=', 'crm.lead'),
                                         ('store', '=', True),
                                         ('ttype', 'in', ('char',
                                                          'date',
                                                          'datetime',
                                                          'float',
                                                          'html',
                                                          'integer',
                                                          'monetary',
                                                          'many2one',
                                                          'selection',
                                                          'phone',
                                                          'text'))],
                                 ondelete='cascade',
                                 required=True)
    facebook_field = fields.Char(string='Facebook Field', required=True)

    _sql_constraints = [
        ('map_unique', 'unique(odoo_field_id, facebook_field)', 'Default Mapping must be unique')
    ]
