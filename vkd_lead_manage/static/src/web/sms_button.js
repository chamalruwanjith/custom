/** @odoo-module **/

import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {SendSMSButton} from '@sms/components/sms_button/sms_button';

patch(SendSMSButton.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    get smsHref() {
        const phone = this.props.record.data[this.props.name];
        return phone ? "sms:" + phone.replace(/\s+/g, "") : null;
    },

    async onClick() {
        const smsLink = this.smsHref;
        if (smsLink) {
            if (this.props.record.resModel === 'crm.lead') {
                const result = await this.env.services.orm.call(
                    "crm.lead",
                    "update_attend_time",
                    [[this.props.record.resId], 'sms'],
                );
                if (result) {
                    this.notification.add("Attend time updated and stage advanced", {type: "success"});
                }
            }
            window.location.href = smsLink;
        } else {
            this.displayNotification({
                title: _t("Error"),
                message: _t("No valid phone number is available."),
                type: "warning",
            });
        }
    }
});
