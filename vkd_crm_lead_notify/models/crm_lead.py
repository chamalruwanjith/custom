# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        leads = super(CrmLead, self).create(vals_list)

        for lead in leads:
            if lead.user_id:
                lead.with_context(skip_mail_notify=True)._send_mobile_push_notification()

        return leads

    def write(self, vals):
        old_users = {lead.id: lead.user_id.id for lead in self}
        res = super(CrmLead, self).write(vals)

        if 'user_id' in vals and vals.get('user_id'):
            for lead in self:
                if lead.user_id.id != old_users.get(lead.id):
                    lead.with_context(skip_mail_notify=True)._send_mobile_push_notification()

        return res

    def _send_mobile_push_notification(self):
        self.ensure_one()

        if not self.user_id or not self.user_id.partner_id.ocn_token:
            _logger.info("No OCN token for user %s, falling back to standard notification",
                         self.user_id.name if self.user_id else "None")
            self._fallback_notification()
            return

        icp_sudo = self.env['ir.config_parameter'].sudo()
        if not icp_sudo.get_param('odoo_ocn.project_id') or not icp_sudo.get_param('mail_mobile.enable_ocn'):
            _logger.info("OCN not configured, falling back to standard notification")
            self._fallback_notification()
            return

        try:
            base_url = icp_sudo.get_param('web.base.url')
            lead_action = self.env.ref('crm.crm_lead_action_pipeline')

            lead_url = f"{base_url}/web#id={self.id}&model=crm.lead&view_type=form&action={lead_action.id}"

            payload = {
                'author_name': 'Facebook Lead',
                'subject': f"New Lead: {self.name}",
                'body': f"You have been assigned a new lead: {self.name}",

                'model': 'crm.lead',
                'res_model': 'crm.lead',
                'res_id': self.id,
                'action': lead_action.id,
                'action_id': lead_action.id,

                'target_url': lead_url,
                'target_action': 'crm.crm_lead_action_pipeline',

                'android_channel_id': 'CrmLead',
                'db_id': self.env['res.config.settings']._get_ocn_uuid(),

                'bypass_chat': True,
                'direct_open': True,
            }

            endpoint = self.env['res.config.settings']._get_endpoint()
            params = {
                'ocn_tokens': [self.user_id.partner_id.ocn_token],
                'data': payload,
            }

            iap_tools.iap_jsonrpc(endpoint + '/iap/ocn/send', params=params)
            _logger.info("Direct push notification sent for lead %s to user %s", self.name, self.user_id.name)

        except Exception as e:
            _logger.error("Error sending direct push notification: %s", e)
            self._fallback_notification()

    def _fallback_notification(self):
        """Fallback to standard notification if direct push fails."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        try:
            crm_menu = self.env.ref('crm.crm_menu_leads', raise_if_not_found=False)
            crm_action = self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)

            if crm_menu and crm_action:
                lead_url = f"{base_url}/web#id={self.id}&model=crm.lead&view_type=form&cids=1&menu_id={crm_menu.id}&action={crm_action.id}"
            else:
                lead_url = f"{base_url}/web#id={self.id}&model=crm.lead&view_type=form"
        except:
            lead_url = f"{base_url}/web#id={self.id}&model=crm.lead&view_type=form"

        message_content = Markup(_("""<div>
                    <p>New Lead Assigned: %s</p>
                    <a href="%s" target='_blank'
                       style="display: inline-block; padding: 10px 15px; background-color: #007BFF; color: #FFF; text-decoration: none; border-radius: 5px; font-weight: bold;">
                       View Lead
                    </a>
                </div>""")) % (self.name, lead_url)

        odoobot_id = self.env.ref("base.partner_root").id
        users_to_notify = self.user_id
        try:
            if not users_to_notify:
                # If no user is assigned, send to the general lead notification channel
                channel = self.env['discuss.channel'].sudo().search([('is_lead_notification_channel', '=', True)],
                                                                    limit=1)
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

        except Exception as e:
            _logger.error("Error sending fallback notification: %s", e)
            # Last resort: post on the lead itself
            try:
                self.message_post(
                    body=message_content,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                    partner_ids=self.user_id.partner_id.ids,
                )
            except Exception as e2:
                _logger.error("Failed to send any notification: %s", e2)
