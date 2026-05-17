# -*- coding: utf-8 -*-
from datetime import timedelta
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class UnitReservation(models.Model):
    _name = "unit.reservation"
    _inherit = 'mail.thread'
    _rec_name = "reservation_id"
    _description = "UnitReservation"

    reservation_id = fields.Char(string="Reservation ID", readonly=True, copy=False, default='New')
    sale_agent_id = fields.Many2one(comodel_name='sale.agent', string="Agent", required=True, tracking=True)
    unit_details_id = fields.Many2one('unit.details', string="Unit", required=True, tracking=True)
    apartment_details_id = fields.Many2one(comodel_name='apartment.details', string='Apartment', required=True)
    floor_details_id = fields.Many2one(comodel_name='floor.details', string='Floor')
    reserved_date = fields.Datetime(string="Hold Date", readonly=True)
    tentatively_sold_date = fields.Datetime(string="Tentatively Sold Date", readonly=True)
    sold_date = fields.Date(string="Sold Date", readonly=True)
    expiration_date = fields.Datetime(string="Expiration Date", compute="_compute_expiration_date", store=True)
    reservation_status = fields.Selection([
        ('draft', 'Draft'),
        ('hold', 'Hold'),
        ('reserved', 'Tentatively Sold'),
        ('sold', 'Sold'),
        ('expired', 'Expired'),
        ('cancel', 'Cancel'),
        ('reset', 'Reset to Draft'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one(comodel_name='res.users', string='User', related='sale_agent_id.user_id', store=True,
                              readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer Name')
    discounted_price = fields.Float(string='Discounted Sales Price')
    paid_amount = fields.Float(string='Paid Amount')
    is_million_completion = fields.Boolean(string='One Million Completion')
    first_sale_agent_id = fields.Many2one(comodel_name='sale.agent', string='Sale Agent 1')
    second_sale_agent_id = fields.Many2one(comodel_name='sale.agent', string='Sale Agent 2')
    ihm_agent = fields.Many2one(comodel_name='ihm.agent', string='IHM Agent')
    assist_by = fields.Many2one(comodel_name='sale.agent', string='Assist By')
    first_contact_number = fields.Char(string='Contact Number 1')
    second_contact_number = fields.Char(string='Contact Number 2')
    whatsapp_number = fields.Char(string='Whatsapp Number')
    source_of_sale = fields.Selection([
        ('banner', 'Banner'),
        ('leaflet', 'Leaflet'),
        ('hoarding', 'Hoarding'),
        ('personal_contact', 'Personal Contact'),
        ('md_contact', 'MD Contact'),
        ('outdoor_campaign', 'Outdoor Campaign'),
        ('direct_visit', 'Direct Visit'),
        ('sms', 'SMS'),
        ('fb_comment', 'FB Comment'),
        ('whatsapp', 'WhatsApp'),
        ('chatbot', 'Chatbot'),
        ('hotline', 'Hotline'),
        ('Existing_Customer', 'Existing Customer'),
        ('Existing_Customer_Recommendation', 'Existing Customer Recommendation'),
        ('other', 'Other'),
    ], string='Source')
    other_source_of_sale = fields.Char(string='Other Source')
    existing_apartment_id = fields.Many2one(comodel_name='apartment.details', string='Existing Project')
    existing_unit_id = fields.Many2one(comodel_name='unit.details', string='Existing Unit')
    existing_customer_id = fields.Many2one(comodel_name='res.partner', string='Existing Customer')
    existing_customer_apartment_id = fields.Many2one(comodel_name='apartment.details',
                                                     string='Existing Customer Project')
    existing_customer_unit_id = fields.Many2one(comodel_name='unit.details', string='Existing Customer Unit')
    is_ceiling_rate_applicable = fields.Boolean(string='Dollar/Ceiling Rate Not Applicable')
    crm_team_id = fields.Many2one(comodel_name='crm.team', string='Sales Team')
    sale_order_count = fields.Integer(string='Sale Orders', compute='_compute_sale_order_count')
    product_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Price List')

    condition_letter_attachment = fields.Many2one('ir.attachment', string="Condition Letter PDF Attachment")
    payment_reference_attachment1 = fields.Many2one('ir.attachment', string="Payment Reference Attachment 1")
    payment_reference_attachment2 = fields.Many2one('ir.attachment', string="Payment Reference Attachment 2")
    condition_letter_file = fields.Binary(related="condition_letter_attachment.datas", string="Condition Letter File",
                                          readonly=True)
    condition_letter_filename = fields.Char(related="condition_letter_attachment.name",
                                            string="Condition Letter Filename", readonly=True)
    payment_reference_file1 = fields.Binary(related="payment_reference_attachment1.datas",
                                            string="Payment Reference File 1", readonly=True)
    payment_reference_filename1 = fields.Char(related="payment_reference_attachment1.name",
                                              string="Payment Reference Filename", readonly=True)
    payment_reference_file2 = fields.Binary(related="payment_reference_attachment2.datas",
                                            string="Payment Reference File 2", readonly=True)
    payment_reference_filename2 = fields.Char(related="payment_reference_attachment2.name",
                                              string="Payment Reference Filename", readonly=True)
    is_team_leader_notify_sale = fields.Boolean(string="Team Leader Notify Sale", default=False, readonly=True)

    @api.model
    def create(self, vals):
        """Create reservation with hold limit validation and auto-generated sequence number."""
        portal_user_id = self.env.context.get('portal_user_id')
        sale_agent_id = vals.get('sale_agent_id')
        apartment_id = vals.get('apartment_details_id')
        unit_id = vals.get('unit_details_id')

        if unit_id:
            unit = self.env['unit.details'].sudo().browse(unit_id)
            if unit.unit_status == 'hold':
                error_message = _('This unit is already on hold. Cannot create a reservation.')
                raise ValidationError(error_message)

        if sale_agent_id and apartment_id:
            hold_limit = int(
                self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit'))
            current_holds = self.env['unit.reservation'].sudo().search_count([
                ('sale_agent_id', '=', sale_agent_id),
                ('apartment_details_id', '=', apartment_id),
                ('reservation_status', '=', 'hold')
            ])
            if current_holds >= hold_limit:
                agent = self.env['sale.agent'].sudo().browse(sale_agent_id)
                apartment = self.env['apartment.details'].sudo().browse(apartment_id)
                error_message = _(
                    'The agent %s has reached the hold limit of %s units for the apartment %s.'
                ) % (agent.full_name, hold_limit, apartment.apartment_name)
                raise ValidationError(error_message)

        if vals.get('reservation_id', 'New') == 'New':
            vals['reservation_id'] = self.env['ir.sequence'].sudo().next_by_code('unit.reservation') or 'New'

        # Run as the portal agent user so chatter logs show the actual agent, not Administrator
        creator = self.with_user(portal_user_id).sudo() if portal_user_id else self
        return super(UnitReservation, creator).create(vals)

    @api.model
    def write_and_return(self, reservation_id, vals):
        """Write values to a reservation and return True (utility method for portal operations)."""
        self.sudo().browse(reservation_id).write(vals)
        return True

    def action_unit_hold(self):
        """Place unit on hold with agent limit validation and send hold confirmation email."""
        sudo_self = self.sudo()
        portal_user_id = self.env.context.get('portal_user_id')

        hold_limit = int(sudo_self.env['ir.config_parameter'].get_param('vkd_property_management.hold_unit_limit'))
        current_holds = sudo_self.env['unit.reservation'].search_count([
            ('sale_agent_id', '=', sudo_self.sale_agent_id.id),
            ('apartment_details_id', '=', sudo_self.apartment_details_id.id),
            ('reservation_status', '=', 'hold')
        ])

        if current_holds >= hold_limit:
            error_message = _(
                'The agent %s has reached the hold limit of %s units for the apartment %s.'
            ) % (sudo_self.sale_agent_id.full_name, hold_limit, sudo_self.apartment_details_id.apartment_name)
            raise ValidationError(error_message)

        if sudo_self.unit_details_id.unit_status == 'hold':
            error_message = _('This unit is already on hold.')
            raise ValidationError(error_message)

        # Use the portal agent user for write/chatter so logs show the real agent name
        actor = self.with_user(portal_user_id).sudo() if portal_user_id else sudo_self
        actor.write({'reservation_status': 'hold', 'reserved_date': fields.Datetime.now()})
        actor._update_unit_status('hold')
        actor._update_unit_activity('hold')

        template = sudo_self.env.ref('vkd_property_management.sale_agent_hold_email_template', raise_if_not_found=False)
        if template:
            template.send_mail(sudo_self.id, force_send=True)

        return True

    def action_unit_reserve(self):
        """Reserve the unit and create a Sales Order Quotation."""
        self.ensure_one()

        unit = self.unit_details_id
        product = self.env['product.product'].search([('default_code', '=', unit.unit_code)], limit=1)

        if not product:
            raise ValidationError(
                _('No product found for this unit. Please ensure the product is created in Inventory.'))

        pricelist_price = (
            self.product_pricelist_id._get_product_price(product, 1.0)
            if self.product_pricelist_id else product.lst_price
        )

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': self.discounted_price or pricelist_price,
            })],
            'origin': self.reservation_id,
            'pricelist_id': self.product_pricelist_id.id,
        })

        self.write({'reservation_status': 'reserved', 'tentatively_sold_date': fields.Datetime.now()})
        self._update_unit_status('reserved')
        self._update_unit_activity('reserved')

        self.action_notify_sale_team_leader()

        return {
            'name': _('Quotation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
        }

    def action_unit_reserve_from_agent(self):
        """Reserve the unit and create a Sales Order Quotation from portal."""
        self.ensure_one()

        sudo_self = self.sudo()
        portal_user_id = self.env.context.get('portal_user_id')
        actor = self.with_user(portal_user_id).sudo() if portal_user_id else sudo_self

        _logger.info("Starting reservation process for Reservation ID: %s, Agent: %s",
                     sudo_self.reservation_id, sudo_self.sale_agent_id.full_name)

        try:
            if not sudo_self.unit_details_id:
                error_msg = _('Unit details not found for reservation %s') % sudo_self.reservation_id
                _logger.error(error_msg)
                raise UserError(error_msg)

            unit = sudo_self.unit_details_id
            _logger.info("Processing unit: %s (Status: %s)", unit.unit_code, unit.unit_status)

            if not sudo_self.partner_id:
                error_msg = _('Customer is required. Please select a customer before reserving the unit.')
                _logger.error("Reservation %s: %s", sudo_self.reservation_id, error_msg)
                raise UserError(error_msg)

            _logger.info("Customer selected: %s (ID: %s)", sudo_self.partner_id.name, sudo_self.partner_id.id)

            if not sudo_self.product_pricelist_id:
                error_msg = _('Price list is required. Please select a price list before reserving the unit.')
                _logger.error("Reservation %s: %s", sudo_self.reservation_id, error_msg)
                raise UserError(error_msg)

            _logger.info("Price list: %s (ID: %s)", sudo_self.product_pricelist_id.name,
                         sudo_self.product_pricelist_id.id)

            product = sudo_self.env['product.product'].search([('default_code', '=', unit.unit_code)], limit=1)

            if not product:
                error_msg = _(
                    'No product found for unit %s. Please contact administrator to create the product in Inventory.') % unit.unit_code
                _logger.error("Reservation %s: %s", sudo_self.reservation_id, error_msg)
                raise UserError(error_msg)

            _logger.info("Product found: %s (ID: %s, Price: %s)", product.name, product.id, product.lst_price)

            try:
                pricelist_price = sudo_self.product_pricelist_id._get_product_price(product, 1.0)

                sale_order_values = {
                    'partner_id': sudo_self.partner_id.id,
                    'pricelist_id': sudo_self.product_pricelist_id.id,
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'price_unit': sudo_self.discounted_price or pricelist_price,
                    })],
                    'origin': sudo_self.reservation_id,
                }

                _logger.info("Creating sale order for reservation %s with values: %s",
                             sudo_self.reservation_id, sale_order_values)

                sale_order = sudo_self.env['sale.order'].create(sale_order_values)
                _logger.info("Sale order created successfully: SO-%s for reservation %s",
                             sale_order.id, sudo_self.reservation_id)

            except Exception as e:
                error_msg = _('Failed to create sale order: %s') % str(e)
                _logger.error("Reservation %s: %s", sudo_self.reservation_id, error_msg, exc_info=True)
                raise UserError(error_msg)

            try:
                # Use actor (portal agent user) so chatter shows the real agent name
                actor.write({'reservation_status': 'reserved', 'tentatively_sold_date': fields.Datetime.now()})
                _logger.info("Reservation %s status updated to 'reserved'", sudo_self.reservation_id)
            except Exception as e:
                _logger.error("Failed to update reservation %s status: %s", sudo_self.reservation_id, str(e),
                              exc_info=True)
                raise

            try:
                sudo_self._update_unit_status('reserved')
                _logger.info("Unit %s status updated to 'reserved'", unit.unit_code)
            except Exception as e:
                _logger.error("Failed to update unit %s status: %s", unit.unit_code, str(e), exc_info=True)

            try:
                actor._update_unit_activity('reserved')
                _logger.info("Activity record created for unit %s reservation", unit.unit_code)
            except Exception as e:
                _logger.error("Failed to create activity record for %s: %s", unit.unit_code, str(e), exc_info=True)

            try:
                sudo_self.action_notify_sale_team_leader()
                _logger.info("Team leader notified for reservation %s", sudo_self.reservation_id)
            except Exception as e:
                _logger.warning("Failed to notify team leader for reservation %s: %s",
                                sudo_self.reservation_id, str(e), exc_info=True)

            _logger.info("Reservation process completed successfully for %s", sudo_self.reservation_id)
            return True

        except (UserError, ValidationError) as e:
            _logger.error("Reservation %s failed with user error: %s", sudo_self.reservation_id, str(e))
            raise
        except Exception as e:
            error_msg = _('Unexpected error during reservation: %s') % str(e)
            _logger.error("Reservation %s: %s", sudo_self.reservation_id, error_msg, exc_info=True)
            raise UserError(error_msg)

    def action_set_cancel(self):
        """Cancel the reservation if there are no confirmed sale orders linked to the reserved unit."""
        for reservation in self:
            sale_orders = self.env['sale.order.line'].search([
                ('product_id.default_code', '=', reservation.unit_details_id.unit_code)
            ]).mapped('order_id')

            confirmed_orders = sale_orders.filtered(lambda so: so.state == 'sale')
            if confirmed_orders:
                raise ValidationError(
                    _("The unit linked to this reservation has a confirmed sale order "
                      "and cannot be canceled. Please handle the sale order(s) first.")
                )

            quotation_orders = sale_orders.filtered(lambda so: so.state in ['draft', 'sent'])
            for order in quotation_orders:
                order.action_cancel()

            reservation.write({
                'reservation_status': 'cancel',
                'tentatively_sold_date': False,
                'sold_date': False,
            })

            if reservation.unit_details_id:
                reservation._update_unit_status('available')
                reservation._update_unit_activity('cancel')

    def action_set_reset(self):
        """Reset reservation status to draft and set unit status to available."""
        self.write({'reservation_status': 'draft'})
        self._update_unit_status('available')

    def action_open_sale_orders(self):
        """Open all sale orders linked to this reservation."""
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        action.update({
            'domain': [('origin', '=', self.reservation_id)],
            'context': {'default_origin': self.reservation_id},
            'view_mode': 'tree,form',
        })
        return action

    def action_notify_sale_team_leader(self):
        """Send Discuss channel and email notifications to team leader about new reservation."""
        for record in self:
            _logger.info("Attempting to notify team leader for reservation %s", record.reservation_id)

            if not record.sale_agent_id.crm_team_id:
                _logger.warning("Reservation %s: Agent %s has no CRM team assigned. Skipping notification.",
                                record.reservation_id, record.sale_agent_id.full_name)
                return

            team_leader = record.sale_agent_id.crm_team_id.user_id

            if not team_leader:
                _logger.warning("Reservation %s: CRM team '%s' has no team leader assigned. Skipping notification.",
                                record.reservation_id, record.sale_agent_id.crm_team_id.name)
                return

            _logger.info("Team leader found: %s (ID: %s)", team_leader.name, team_leader.id)

            try:
                notification_message = Markup(_("""
                                <p><strong>Sales Submission Alert</strong></p>
                                <p>%s submitted a reservation for Unit %s in %s.</p>
                            """)) % (
                    record.sale_agent_id.full_name,
                    record.unit_details_id.unit_code,
                    record.apartment_details_id.apartment_name
                )
            except Exception as e:
                _logger.error("Failed to format notification message for %s: %s",
                              record.reservation_id, str(e), exc_info=True)
                notification_message = Markup(
                    _("<p>New reservation submitted by %s</p>") % record.sale_agent_id.full_name)

            try:
                if team_leader.partner_id:
                    odoobot_id = self.env.ref("base.partner_root", raise_if_not_found=False)
                    if odoobot_id:
                        channel = self.env['discuss.channel'].channel_get([team_leader.partner_id.id])
                        channel.sudo().message_post(
                            body=notification_message,
                            author_id=odoobot_id.id,
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                        _logger.info("Discuss channel message sent to team leader for reservation %s",
                                     record.reservation_id)
                    else:
                        _logger.warning("Odoobot reference not found. Skipping Discuss notification.")
            except Exception as e:
                _logger.warning("Failed to send Discuss channel notification for %s: %s",
                                record.reservation_id, str(e), exc_info=True)

            try:
                if not team_leader.login:
                    _logger.warning("Reservation %s: Team leader %s has no email/login configured. Skipping email.",
                                    record.reservation_id, team_leader.name)
                    return

                template = self.env.ref('vkd_property_management.team_leader_notification_email_template',
                                        raise_if_not_found=False)

                if template:
                    template.send_mail(record.id, force_send=True)
                    _logger.info("Email notification sent to team leader for reservation %s", record.reservation_id)
                else:
                    _logger.warning("Email template not found for reservation %s", record.reservation_id)

            except Exception as e:
                _logger.error("Failed to send email notification for reservation %s: %s",
                              record.reservation_id, str(e), exc_info=True)

    def action_notify_sale_agent(self):
        """Notify the sale agent that their Tentatively Sold request is confirmed by the team leader."""
        for record in self:
            if not record.sale_agent_id.user_id.login:
                raise ValidationError(
                    _("The sales agent %s does not have an email configured.") % record.sale_agent_id.full_name
                )

            template = self.env.ref(
                'vkd_property_management.tentatively_sold_notification_email_template',
                raise_if_not_found=False
            )

            template.send_mail(record.id, force_send=True)

    def _update_unit_status(self, status):
        """Update the linked unit's status based on reservation status change."""
        sudo_self = self.sudo()
        if sudo_self.unit_details_id:
            status_map = {
                'hold': 'hold',
                'reserved': 'reserved',
                'sold': 'sold',
                'expired': 'available',
                'cancel': 'available',
                'reset': 'available'
            }
            new_status = status_map.get(status, 'available')
            sudo_self.unit_details_id.write({'unit_status': new_status})

    def _update_unit_activity(self, activity_type):
        """Create activity log entry for unit status change."""
        self.ensure_one()
        self.env['unit.activity'].sudo().create({
            'unit_reservation_id': self.id,
            'user_id': self.env.uid,
            'unit_details_id': self.unit_details_id.id,
            'apartment_details_id': self.apartment_details_id.id,
            'activity_type': activity_type,
        })

    @api.depends('reserved_date')
    def _compute_expiration_date(self):
        """Calculate hold expiration date based on system configuration days."""
        for record in self:
            if record.reserved_date:
                hold_expiration_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_expiration_days'))
                record.expiration_date = record.reserved_date + timedelta(days=hold_expiration_days)
            else:
                record.expiration_date = False

    @api.model
    def check_hold_expiration(self):
        """Check if any holds have expired and notify relevant sales agents."""
        now = fields.Datetime.now()
        today_date = now.date()

        reservations = self.search([('reservation_status', '=', 'hold')])
        template_reminder = self.env.ref(
            'vkd_property_management.sale_agent_hold_reminder_template',
            raise_if_not_found=False
        )
        template_expired = self.env.ref(
            'vkd_property_management.sale_agent_expired_hold_notification_email_template',
            raise_if_not_found=False
        )

        for reservation in reservations:
            if reservation.expiration_date:
                expiration_datetime = reservation.expiration_date
                expiration_date = expiration_datetime.date()

                if expiration_date == today_date + timedelta(days=1) and template_reminder:
                    template_reminder.send_mail(reservation.id, force_send=True)

                elif expiration_datetime < now:
                    reservation.write({'reservation_status': 'expired'})
                    reservation._update_unit_status('available')
                    reservation._update_unit_activity('expired')

                    if template_expired:
                        template_expired.send_mail(reservation.id, force_send=True)

    @api.depends('reservation_id')
    def _compute_sale_order_count(self):
        """Compute the number of sale orders linked to this reservation."""
        for record in self:
            record.sale_order_count = self.env['sale.order'].search_count([('origin', '=', record.reservation_id)])
