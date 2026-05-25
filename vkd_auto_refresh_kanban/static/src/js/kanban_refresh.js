/** @odoo-module **/
import {StreamPostKanbanController} from '@social/js/stream_post_kanban_controller';
import {patch} from "@web/core/utils/patch";
import {onMounted, onWillUnmount} from "@odoo/owl";

patch(StreamPostKanbanController.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            this.startAutoRefresh();
        });

        onWillUnmount(() => {
            console.log('Component is being destroyed');
            this.stopAutoRefresh();
        });
    },

    startAutoRefresh() {
        this.shortIntervalId = setInterval(() => {
            this.performRefreshView();
        }, 25000); // 25 seconds

        this.longIntervalId = setInterval(() => {
            this.performRefresh();
        }, 60000); // 60 seconds

        // Perform initial refresh
        this.performRefresh();
        this.performRefreshView();
    },

    stopAutoRefresh() {
        if (this.shortIntervalId) {
            clearInterval(this.shortIntervalId);
        }
        if (this.longIntervalId) {
            clearInterval(this.longIntervalId);
        }
    },


    performRefresh() {
        if (this._onRefreshStats) {
            this._onRefreshStats();
            console.log("Content refreshed status");
        }
    },

    performRefreshView() {
        if (this._refreshView) {
            this._refreshView();
            console.log("Content refreshed automatically");
        } else if (this.model && this.model.load) {
            this.model.load();
        } else {
            console.error("No suitable refresh method found");
        }

    }
});
