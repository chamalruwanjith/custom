from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    crm_team_id = fields.Many2one('crm.team', string='CRM Team', compute='_compute_crm_team_id', store=True)

    @api.depends_context('uid')
    def _compute_crm_team_id(self):
        """Compute the CRM team for the user"""
        for user in self:
            crm_team_member = self.env['crm.team.member'].search([('user_id', '=', user.id)], limit=1)
            user.crm_team_id = crm_team_member.crm_team_id if crm_team_member else False

