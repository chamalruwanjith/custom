/* @odoo-module */

import {useService} from "@web/core/utils/hooks";
import {patch} from "@web/core/utils/patch";
import {EmailField } from "@web/views/fields/email/email_field";

patch(EmailField.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    /**
     * Called when the phone number is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async onLinkClicked(ev) {
        if (this.props.record.resModel === 'crm.lead') {
            const result = await this.env.services.orm.call(
                "crm.lead",
                "update_attend_time",
                [[this.props.record.resId], 'email'],
            );
            if (result) {
                this.notification.add("Attend time updated and stage advanced", {type: "success"});
            }
        }
    },
});
