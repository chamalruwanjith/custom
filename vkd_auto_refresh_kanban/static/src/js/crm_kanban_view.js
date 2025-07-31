/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { onMounted, onWillUnmount } from "@odoo/owl";

const crmKanbanView = registry.category("views").get("crm_kanban");

patch(crmKanbanView.Controller.prototype, {
    setup() {
        super.setup();

        this.refreshIntervalTime = 30000; // 30 seconds
        this.refreshIntervalId = null;

        onMounted(() => {
            console.log("CRM Kanban mounted - starting auto-refresh");
            this.startAutoRefresh();
        });

        onWillUnmount(() => {
            console.log("CRM Kanban will unmount - stopping auto-refresh");
            this.stopAutoRefresh();
        });

        // Handle page visibility changes
        this.visibilityChangeHandler = () => {
            if (document.hidden) {
                console.log("Document hidden - pausing auto-refresh");
                this.stopAutoRefresh();
            } else {
                console.log("Document visible - resuming auto-refresh");
                this.startAutoRefresh();
            }
        };
        document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    },

    startAutoRefresh() {
        // Clear any existing interval first
        this.stopAutoRefresh();

        this.refreshIntervalId = setInterval(() => {
            this.performRefresh();
        }, this.refreshIntervalTime);

        console.log("Auto-refresh started with interval:", this.refreshIntervalId);
    },

    stopAutoRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
            console.log("Auto-refresh stopped");
        }

        // Clean up visibility change listener
        if (this.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
            this.visibilityChangeHandler = null;
        }
    },

    async performRefresh() {
        try {
            console.log("Auto-refresh triggered");

            // Check if model and required methods exist
            if (!this.model || !this.model.root || typeof this.model.root.load !== 'function') {
                console.warn("Model or load method not available, skipping refresh");
                return;
            }

            console.log("Loading model root...");
            await this.model.root.load();

            // Update progress bars if they exist
            if (this.progressBarState) {
                console.log("Updating progress bar state...");
                try {
                    if (typeof this.progressBarState.updateCounts === 'function') {
                        this.progressBarState.updateCounts();
                    }
                } catch (progressError) {
                    console.log("Progress bar update failed:", progressError.message);
                }
            }

            // Re-render the view
            if (typeof this.render === 'function') {
                console.log("Re-rendering view...");
                this.render(true);
                console.log("Auto-refresh completed successfully");
            } else {
                console.warn("Render method not available");
            }

        } catch (error) {
            console.warn('Auto-refresh failed:', error.message || error);
        }
    },
});

console.log("CRM Kanban Controller patched with Owl lifecycle auto-refresh");