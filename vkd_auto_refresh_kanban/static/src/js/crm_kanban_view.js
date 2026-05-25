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
            this._cleanupVisibilityListener();
        });

        // Pause refresh when tab is hidden, resume when visible again.
        // Defined once in setup and never nullified so the listener stays registered.
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
        // Do NOT remove or nullify visibilityChangeHandler here —
        // it must stay registered so tab-show can restart the interval.
        // It is only removed in onWillUnmount via _cleanupVisibilityListener().
    },

    _cleanupVisibilityListener() {
        if (this.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
            this.visibilityChangeHandler = null;
        }
    },

    async performRefresh() {
        try {
            if (!this.model || !this.model.root || typeof this.model.root.load !== 'function') {
                return;
            }
            // model.root.load() updates reactive state; OWL re-renders automatically.
            // Do NOT call this.render() here — it causes a double-render every cycle
            // which accumulates unreleased DOM nodes and leads to OOM crashes.
            await this.model.root.load();
        } catch (error) {
            console.warn('Auto-refresh failed:', error.message || error);
        }
    },
});

console.log("CRM Kanban Controller patched with Owl lifecycle auto-refresh");