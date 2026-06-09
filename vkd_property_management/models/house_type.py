# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HouseType(models.Model):
    _name = "house.type"
    _rec_name = "house_type_name"
    _description = "House Type Details"

    house_type_name = fields.Char(string="House Type")
    house_type_description = fields.Char(string="House Type Description")
