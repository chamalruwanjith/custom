from markupsafe import Markup

from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        lead = super(CrmLead, self).create(vals)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        try:
            crm_menu = self.env.ref('crm.crm_menu_leads', raise_if_not_found=False)
            crm_action = self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)

            if crm_menu and crm_action:
                lead_url = f"{base_url}/web?#id={lead.id}&model=crm.lead&view_type=form&cids=1&menu_id={crm_menu.id}&action={crm_action.id}"
            else:
                lead_url = f"{base_url}/web?#id={lead.id}&model=crm.lead&view_type=form"
        except:
            lead_url = f"{base_url}/web?#id={lead.id}&model=crm.lead&view_type=form"

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
            # If no user is assigned, send to the general lead notification channel
            channel = self.env['discuss.channel'].sudo().search([('is_lead_notification_channel', '=', True)], limit=1)

            if channel:
                channel.message_post(
                    body=message_content,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
        else:
            channel = self.env['discuss.channel'].channel_get([odoobot_id, users_to_notify.partner_id.id])
            channel.sudo().message_post(
                body=message_content,
                author_id=odoobot_id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        return lead