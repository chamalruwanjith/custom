from odoo import models, fields, api


class CrmFacebookFormField(models.Model):
    _name = 'crm.facebook.form.field'
    _description = 'Facebook form fields'

    form_id = fields.Many2one('crm.facebook.form', required=True, ondelete='cascade', string='Form')
    name = fields.Char(string='Name')
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
                                 ondelete='set null',
                                 required=False)
    facebook_field= fields.Char(string='Facebook Field', required=True)

    def action_guess_mapping(self):
        Mapping = self.env['crm.facebook.form.mapping']
        for rec in self:
            odoo_field = Mapping.match_odoo_field(rec.facebook_field)
            if odoo_field:
                rec.odoo_field_id = odoo_field

    _sql_constraints = [
        ('field_unique', 'unique(form_id, odoo_field_id, facebook_field)', 'Mapping must be unique per form')
    ]
