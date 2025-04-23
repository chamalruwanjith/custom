from odoo import api, fields, models, _


class TowerDetails(models.Model):
    _name = "tower.details"
    _rec_name = "tower_name"
    _description = "Tower Details"

    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', required=True)
    tower_name = fields.Char(string='Tower Name', required=True)
    tower_prefix = fields.Char(string='Tower Code', required=True)
    tower_image = fields.Binary(string='Tower Image')
    floor_details_ids = fields.One2many(comodel_name='floor.details', inverse_name='tower_details_id')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        (
            'unique_tower_prefix_per_apartment',
            'unique(apartment_details_id, tower_prefix)',
            _('The Tower Prefix must be unique within the same Apartment.')
        ),
    ]

    @api.onchange('apartment_details_id', 'tower_name')
    def _onchange_generate_tower_prefix(self):
        """
        Automatically generate the tower prefix based on the selected apartment prefix and tower name.
        """
        if self.apartment_details_id and self.tower_name:
            self.tower_prefix = f"{self.apartment_details_id.apartment_prefix}{self.tower_name.upper()}"
        else:
            self.tower_prefix = False
