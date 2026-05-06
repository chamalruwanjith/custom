# -*- coding: utf-8 -*-
import random
import string
import jwt
from datetime import datetime, timedelta
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class SaleAgent(models.Model):
    _name = "sale.agent"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "full_name"
    _description = "Sale Agent Details"

    email = fields.Char(string="Email")
    password = fields.Char(string="Password")
    full_name = fields.Char(string="Full Name")
    nic = fields.Char(string="NIC")
    mobile = fields.Char(string="Mobile NO")
    agent_id = fields.Char(string="Agent ID")
    crm_team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team")
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    user_id = fields.Many2one(comodel_name='res.users', string='User', required=True)

    registration_token = fields.Char(
        string="Registration Token",
        readonly=True,
        help="JWT token for agent registration. Valid for 48 hours."
    )

    registration_link = fields.Text(
        string="Registration Link",
        readonly=True,
        help="JWT registration link sent to the agent. Valid for 48 hours."
    )

    registration_link_sent_date = fields.Datetime(
        string="Link Sent Date",
        readonly=True,
        help="Date and time when the registration link was sent"
    )

    registration_token_expiry = fields.Datetime(
        string="Token Expiry",
        readonly=True,
        help="Date and time when the registration token expires"
    )

    def generate_registration_token(self):
        """Generate a JWT registration token valid for 48 hours."""
        self.ensure_one()
        jwt_secret = 'homelands-web-app-for-sale-agent'

        expiry_time = datetime.utcnow() + timedelta(hours=48)

        payload = {
            'agent_id': self.id,
            'email': self.user_id.login if self.user_id and self.user_id.login else '',
            'purpose': 'registration',
            'exp': expiry_time,
            'iat': datetime.utcnow()
        }

        token = jwt.encode(payload, jwt_secret, algorithm='HS256')

        # Store token and expiry in database
        self.write({
            'registration_token': token,
            'registration_token_expiry': expiry_time
        })

        return token

    def generate_sequence(self):
        """Generate a random 6-character alphanumeric sequence for agent identification."""
        length = 6
        characters = string.ascii_letters + string.digits
        sequence = ''.join(random.choice(characters) for i in range(length))
        return sequence

    @api.model
    def create(self, vals):
        """Create sale agent and automatically add associated user to CRM team."""
        sale_agent = super(SaleAgent, self).create(vals)
        sale_agent._update_crm_team_members()
        return sale_agent

    def write(self, vals):
        """Update sale agent and synchronize CRM team membership changes."""
        res = super(SaleAgent, self).write(vals)
        self._update_crm_team_members()
        return res

    def name_get(self):
        """Return display name as 'Full Name (Agent ID)' for sale agent records."""
        res = []
        for sale_agent in self:
            res.append((sale_agent.id, '%s (%s)' % (sale_agent.full_name, sale_agent.emp_id)))
        return res

    def action_send_agent_invitation(self):
        """Send registration invitation email with JWT token link to the sale agent."""
        for agent in self:
            _logger.info("Starting agent invitation process for Agent ID: %s", agent.id)

            # Validate
            if not agent.user_id or not agent.user_id.login:
                raise UserError(_("Agent must have a valid user with an email address."))

            try:
                registration_token = agent.generate_registration_token()

                base_url = 'http://178.212.35.208:8010'

                registration_link = f"{base_url}/signup?token={registration_token}"
                _logger.info("Registration link: %s", registration_link)

                agent.write({
                    'registration_link': registration_link,
                    'registration_link_sent_date': fields.Datetime.now()
                })

                template = self.env.ref('vkd_property_management.sale_agent_invitation_email_template')
                template.send_mail(agent.id, force_send=True)

                agent.message_post(
                    body=_("Registration invitation sent to %s. Token valid until %s") % (
                        agent.user_id.login,
                        agent.registration_token_expiry.strftime(
                            '%Y-%m-%d %H:%M:%S') if agent.registration_token_expiry else 'N/A'
                    )
                )

            except Exception as e:
                _logger.error("Failed to send invitation to Agent ID %s: %s", agent.id, str(e), exc_info=True)
                raise UserError(_("Failed to send invitation: %s") % str(e))

    def _update_crm_team_members(self):
        """Add the sale agent's associated user as a member of the assigned CRM team."""
        for agent in self:
            if agent.crm_team_id and agent.user_id:
                if agent.user_id.id not in agent.crm_team_id.member_ids.ids:
                    agent.crm_team_id.write({
                        'member_ids': [(4, agent.user_id.id)]
                    })
