import logging
import re

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

    @api.model
    def _normalize_key(self, key):
        """Normalise a Facebook field key for tolerant matching: lowercase,
        collapse any whitespace to '_', and drop trailing '?'/'_'/spaces. So
        'Full name?', 'full_name?', 'full name' and 'full_name' all collapse to
        'full_name'. Facebook auto-generates these punctuation/spacing variants,
        which an exact match would miss."""
        k = (key or '').strip().lower()
        k = re.sub(r'\s+', '_', k)
        k = re.sub(r'[?_]+$', '', k)
        return k

    @api.model
    def match_odoo_field(self, facebook_field):
        """Return the best default Odoo field for a Facebook key: exact match
        first, then a normalised match so Facebook's spacing/punctuation/case
        variants still resolve. Returns an ir.model.fields recordset (empty when
        nothing matches)."""
        exact = self.search([('facebook_field', '=', facebook_field)], limit=1)
        if exact:
            return exact.odoo_field_id
        target = self._normalize_key(facebook_field)
        if not target:
            return self.env['ir.model.fields']
        for mapping in self.search([]):
            if self._normalize_key(mapping.facebook_field) == target:
                return mapping.odoo_field_id
        return self.env['ir.model.fields']
