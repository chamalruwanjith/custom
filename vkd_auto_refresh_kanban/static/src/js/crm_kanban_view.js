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
            this.startAutoRefresh();
        });

        onWillUnmount(() => {
            this.stopAutoRefresh();
        });

        // Handle page visibility changes
        this.visibilityChangeHandler = () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
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

    },

    stopAutoRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
        }

        // Clean up visibility change listener
        if (this.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
            this.visibilityChangeHandler = null;
        }
    },

    async performRefresh() {
        try {
            // Check if model and required methods exist
            if (!this.model || !this.model.root || typeof this.model.root.load !== 'function') {
                return;
            }
            await this.model.root.load();

            // Update progress bars if they exist
            if (this.progressBarState) {
                try {
                    if (typeof this.progressBarState.updateCounts === 'function') {
                        this.progressBarState.updateCounts();
                    }
                } catch (progressError) {
                }
            }

            // Re-render the view
            if (typeof this.render === 'function') {
                this.render(true);
            } else {
                console.warn("Render method not available");
            }

        } catch (error) {
            console.warn('Auto-refresh failed:', error.message || error);
        }
    },
});
