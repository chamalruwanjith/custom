from odoo import fields, models, api


class LeadAllocate(models.Model):
    _inherit = 'lead.allocate'

    facebook_page_id = fields.Many2one(
        'crm.facebook.page', string='Facebook Page', tracking=True,
        help='Restrict this allocation to leads coming from this Facebook page. '
             'Leave empty to act as the catch-all allocation for the team/shift.',
    )

    def _overlap_extra_domain(self):
        # Two allocations only conflict when they target the same Facebook page.
        # This lets a page-specific allocation (e.g. Land Sale) run in parallel
        # with the generic (page-empty) allocation on the same team/shift/date.
        self.ensure_one()
        return [('facebook_page_id', '=', self.facebook_page_id.id)]

    @api.constrains('from_time', 'to_time', 'team_id', 'facebook_page_id')
    def _check_time_overlap(self):
        # Re-register the base constraint so it also re-runs when the page changes.
        return super()._check_time_overlap()
