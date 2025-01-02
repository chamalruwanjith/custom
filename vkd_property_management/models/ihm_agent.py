from odoo import api, fields, models, _


class IhmAgent(models.Model):
    _name = "ihm.agent"
    _rec_name = "ihm_agent_name"
    _description = "IHM Agent Details"

    ihm_agent_name = fields.Char(string="IHM Agent Name")
    ihm_agent_description = fields.Char(string="IHM Agent Description")
