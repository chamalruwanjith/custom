/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {Component} from "@odoo/owl";

export class SendWhatsAppButton extends Component {
    static template = "whatsapp.SendWhatsAppButton";
    static props = ["*"];

    setup() {
        this.title = _t("Send WhatsApp Message");
    }

    // Remove leading zeros from the phone number
    removeLeadingZeros(phoneNumber) {
        if (!phoneNumber) return null;

        // Remove all non-digit characters
        let sanitized = phoneNumber.replace(/\D/g, "");
        if (!sanitized) return null;

        // Remove all leading zeros
        sanitized = sanitized.replace(/^0+/, "");

        return sanitized;
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

        const formattedPhoneNumber = this.removeLeadingZeros(phoneNumber);

        if (formattedPhoneNumber) {
            const whatsappUrl = `whatsapp://send?phone=${formattedPhoneNumber}`;
            console.log(`Original: ${phoneNumber} → Formatted (zeros removed): ${formattedPhoneNumber}`);

            const newTab = window.open(whatsappUrl, "_blank");
            if (!newTab || newTab.closed || typeof newTab.closed === "undefined") {
                window.location.href = whatsappUrl;
            }
        }
    }
}

