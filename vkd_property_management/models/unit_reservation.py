from datetime import timedelta, date
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


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
    reserved_date = fields.Date(string="Hold Date", readonly=True)
    tentatively_sold_date = fields.Date(string="Tentatively Sold Date", readonly=True)
    sold_date = fields.Date(string="Sold Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", compute="_compute_expiration_date", store=True)
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
        sale_agent_id = vals.get('sale_agent_id')
        apartment_id = vals.get('apartment_details_id')
        unit_id = vals.get('unit_details_id')

        # Check if unit is already on hold before creating any record
        if unit_id:
            unit = self.env['unit.details'].browse(unit_id)
            if unit.unit_status == 'hold':
                error_message = _('This unit is already on hold. Cannot create a reservation.')
                raise ValidationError(error_message)

        if sale_agent_id and apartment_id:
            hold_limit = int(
                self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit'))
            current_holds = self.env['unit.reservation'].search_count([
                ('sale_agent_id', '=', sale_agent_id),
                ('apartment_details_id', '=', apartment_id),
                ('reservation_status', '=', 'hold')
            ])
            if current_holds >= hold_limit:
                agent = self.env['sale.agent'].browse(sale_agent_id)
                apartment = self.env['apartment.details'].browse(apartment_id)
                error_message = _(
                    'The agent %s has reached the hold limit of %s units for the apartment %s.'
                ) % (agent.full_name, hold_limit, apartment.apartment_name)
                raise ValidationError(error_message)

        if vals.get('reservation_id', 'New') == 'New':
            vals['reservation_id'] = self.env['ir.sequence'].next_by_code('unit.reservation') or 'New'
        return super(UnitReservation, self).create(vals)

    @api.model
    def write_and_return(self, reservation_id, vals):
        self.browse(reservation_id).write(vals)
        return True

    def action_unit_hold(self):
        hold_limit = int(self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_unit_limit'))
        current_holds = self.env['unit.reservation'].search_count([
            ('sale_agent_id', '=', self.sale_agent_id.id),
            ('apartment_details_id', '=', self.apartment_details_id.id),
            ('reservation_status', '=', 'hold')
        ])
        if current_holds >= hold_limit:
            error_message = _(
                'The agent %s has reached the hold limit of %s units for the apartment %s.'
            ) % (self.sale_agent_id.full_name, hold_limit, self.apartment_details_id.apartment_name)
            raise ValidationError(error_message)
        if self.unit_details_id.unit_status == 'hold':
            error_message = _('This unit is already on hold.')
            raise ValidationError(error_message)
        self.write({'reservation_status': 'hold', 'reserved_date': date.today()})
        self._update_unit_status('hold')

        template = self.env.ref('vkd_property_management.sale_agent_hold_email_template', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

        return True

    def action_unit_reserve(self):
        """Reserve the unit and create a Sales Order Quotation."""
        self.ensure_one()

        unit = self.unit_details_id
        product = self.env['product.product'].search([('default_code', '=', unit.unit_code)], limit=1)

        if not product:
            raise ValidationError(
                _('No product found for this unit. Please ensure the product is created in Inventory.'))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': self.discounted_price or product.lst_price,
            })],
            'origin': self.reservation_id,
            'pricelist_id': self.product_pricelist_id.id,
        })

        self.write({'reservation_status': 'reserved', 'tentatively_sold_date': fields.Date.today()})
        self._update_unit_status('reserved')

        self.action_notify_sale_team_leader()

        return {
            'name': _('Quotation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
        }

    def action_unit_reserve_from_agent(self):
        """Reserve the unit and create a Sales Order Quotation."""
        self.ensure_one()

        unit = self.unit_details_id
        product = self.env['product.product'].search([('default_code', '=', unit.unit_code)], limit=1)

        if not product:
            raise ValidationError(
                _('No product found for this unit. Please ensure the product is created in Inventory.'))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'pricelist_id': self.product_pricelist_id.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': self.discounted_price or product.lst_price,
            })],
            'origin': self.reservation_id,
        })

        self.write({'reservation_status': 'reserved'})
        self._update_unit_status('reserved')

        self.action_notify_sale_team_leader()

        return True

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

    def action_set_reset(self):
        self.write({'reservation_status': 'draft'})
        self._update_unit_status('available')

    def action_open_sale_orders(self):
        """Open related sale orders in a tree view."""
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        action.update({
            'domain': [('origin', '=', self.reservation_id)],
            'context': {'default_origin': self.reservation_id},
            'view_mode': 'tree,form',
        })
        return action

    def action_notify_sale_team_leader(self):
        """Notify the team leader about the sales submission."""
        for record in self:
            team_leader = record.sale_agent_id.crm_team_id.user_id
            odoobot_id = self.env.ref("base.partner_root").id

            notification_message = Markup(_("""
                            <p><strong>Sales Submission Alert</strong></p>
                            <p>%s submitted a reservation for Unit %s in %s.</p>
                        """))

            # Send Notification to the team leader
            if team_leader:
                channel = self.env['discuss.channel'].channel_get([team_leader.partner_id.id])
                channel.sudo().message_post(
                    body=notification_message,
                    author_id=odoobot_id,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

            if not team_leader or not team_leader.login:
                raise ValidationError(
                    _("The team leader for the sales agent %s does not have an email configured.")
                    % record.sale_agent_id.full_name
                )

            template = self.env.ref('vkd_property_management.team_leader_notification_email_template',
                                    raise_if_not_found=False)

            template.send_mail(record.id, force_send=True)

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
        if self.unit_details_id:
            status_map = {
                'hold': 'hold',
                'reserved': 'reserved',
                'sold': 'sold',
                'expired': 'available',
                'cancel': 'available',
                'reset': 'available'
            }
            new_status = status_map.get(status, 'available')
            self.unit_details_id.write({'unit_status': new_status})

    @api.depends('reserved_date')
    def _compute_expiration_date(self):
        for record in self:
            if record.reserved_date:
                hold_expiration_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('vkd_property_management.hold_expiration_days'))
                expiration_date = fields.Date.from_string(record.reserved_date) + timedelta(days=hold_expiration_days)
                record.expiration_date = fields.Date.to_string(expiration_date)
            else:
                record.expiration_date = False

    @api.model
    def check_hold_expiration(self):
        """Check if any holds have expired and notify relevant sales agents."""
        today = date.today()
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
            expiration_date = fields.Date.from_string(reservation.expiration_date)
            if expiration_date:
                # If the hold expires tomorrow, send a reminder email.
                if expiration_date == today + timedelta(days=1) and template_reminder:
                    template_reminder.send_mail(reservation.id, force_send=True)

                # If the hold has expired, update status and notify agents.
                elif expiration_date < today:
                    reservation.write({'reservation_status': 'expired'})
                    reservation._update_unit_status('available')

                    if template_expired:
                        template_expired.send_mail(reservation.id, force_send=True)

    @api.depends('reservation_id')
    def _compute_sale_order_count(self):
        """Compute the number of sale orders linked to this reservation."""
        for record in self:
            record.sale_order_count = self.env['sale.order'].search_count([('origin', '=', record.reservation_id)])
