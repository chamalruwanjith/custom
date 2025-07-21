from markupsafe import Markup

from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        lead = super(CrmLead, self).create(vals)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        lead_url = f"{base_url}/web#id={lead.id}&model=crm.lead&view_type=form"
        message_content = Markup(_("""<div>
            <p>New Lead Created: %s</p>
            <a href="%s" target='_blank'
               style="display: inline-block; padding: 10px 15px; background-color: #007BFF; color: #FFF; text-decoration: none; border-radius: 5px; font-weight: bold;">
               View Lead
            </a>
        </div>""")) % (lead.name, lead_url)

        odoobot_id = self.env.ref("base.partner_root").id
        users_to_notify = lead.user_id

        if not users_to_notify:
            channel = self.env['discuss.channel'].sudo().search([('is_lead_notification_channel', '=', True)], limit=1)

            if channel:
                channel.message_post(
                    body=message_content,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

        # for user in users_to_notify:
        channel = self.env['discuss.channel'].channel_get([odoobot_id, users_to_notify.partner_id.id])
        channel.sudo().message_post(
            body=message_content,
            author_id=odoobot_id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # template = self.env.ref('vkd_crm_lead_notify.sale_team_new_lead_email_template',
        #                        raise_if_not_found=False)

        # template.send_mail(lead.id, force_send=True)

        # base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # menu_id = 310  # Replace with the actual menu_id
        # action_id = 440  # Replace with the actual action_id
        # lead_url = (f"{base_url}/web?debug=1#id={lead.id}&model=crm.lead&view_type=form"
        #             f"&cids=1&menu_id={menu_id}&action={action_id}")
        #
        # # Define the message content
        # message_content = Markup(_("""<div>
        #     <p>New Lead Created: %s</p>
        #     <a href="%s" target="_blank"
        #        style="display: inline-block; padding: 10px 15px; background-color: #007BFF; color: #FFF; text-decoration: none; border-radius: 5px; font-weight: bold;">
        #        View Lead
        #     </a>
        # </div>""")) % (lead.name, lead_url)

        # message_content = Markup(_("""
        #             <div style="margin: 10px 0;">
        #                 <span style="display: block; margin-bottom: 10px;">New Lead Created</span>
        #                 <a href="%s"
        #                    style="display: inline-block; padding: 8px 16px; background-color: #00A09D; color: white; text-decoration: none; border-radius: 4px;"
        #                    class="btn"
        #                    target='_blank'>
        #                     View Lead Details
        #                 </a>
        #             </div>
        #         """)) % (lead_url)
        return lead
