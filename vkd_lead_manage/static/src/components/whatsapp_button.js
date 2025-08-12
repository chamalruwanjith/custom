/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {Component} from "@odoo/owl";

export class SendWhatsAppButton extends Component {
    static template = "whatsapp.SendWhatsAppButton";
    static props = ["*"];

    setup() {
        this.title = _t("Send WhatsApp Message");
    }

    async onClick() {
        await this.props.record.save();
        if (this.props.record.resModel === 'crm.lead') {
            await this.env.services.orm.call(
                "crm.lead",
                "update_attend_time",
                [[this.props.record.resId], 'whatsapp'],
            );
        }
        const phoneNumber = this.props.record.data[this.props.name];
        const sanitizedPhoneNumber = phoneNumber ? phoneNumber.replace(/\D/g, '') : null;

        if (sanitizedPhoneNumber) {
            // const whatsappUrl = `https://api.whatsapp.com/send?phone=${sanitizedPhoneNumber}`;
            const whatsappUrl = `whatsapp://send?phone=${sanitizedPhoneNumber}`;

            const newTab = window.open(whatsappUrl, '_blank');
            if (!newTab || newTab.closed || typeof newTab.closed === 'undefined') {
                window.location.href = whatsappUrl;
            }
        }
    }
}
