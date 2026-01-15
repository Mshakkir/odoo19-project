/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter ONLY for Sale Orders
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this._filterElement = null;

        onMounted(() => {
            // Strict check: Only show on sale.order AND only on Orders menu (not Quotations)
            if (this.shouldShowFilter()) {
                setTimeout(() => this.injectDateFilter(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupFilter();
        });
    },

    shouldShowFilter() {
        // Must be sale.order model
        if (this.props.resModel !== 'sale.order') {
            return false;
        }

        // Check the action's XML ID or name
        const action = this.env.config;

        // Method 1: Check action XML ID (most reliable)
        if (action.xmlId === 'sale.action_orders') {
            return true;
        }

        // Method 2: Check if action name contains "Orders" but not "Quotations"
        if (action.displayName || action.name) {
            const actionName = (action.displayName || action.name).toLowerCase();
            if (actionName.includes('order') && !actionName.includes('quotation')) {
                return true;
            }
        }

        // Method 3: Check domain for sale order states
        if (this.props.domain) {
            const hasOrderState = this.props.domain.some(item =>
                Array.isArray(item) &&
                item[0] === 'state' &&
                (JSON.stringify(item).includes('sale') || JSON.stringify(item).includes('done'))
            );
            if (hasOrderState) {
                return true;
            }
        }

        // Method 4: Check context
        if (this.props.context) {
            if (this.props.context.search_default_sales ||
                this.props.context.default_state === 'sale') {
                return true;
            }
        }

        return false;
    },

    cleanupFilter() {
        if (this._filterElement && this._filterElement.parentNode) {
            this._filterElement.remove();
            this._filterElement = null;
        }
    },

    injectDateFilter() {
        // Clean up any existing filter
        this.cleanupFilter();

        const listView = document.querySelector('.o_list_view');
        if (!listView) return;

        // Check if filter already exists (safety check)
        if (document.querySelector('.sale_date_filter_wrapper_main')) {
            return;
        }

        // Create unique IDs
        const timestamp = Date.now();
        const fromId = `date_from_${timestamp}`;
        const toId = `date_to_${timestamp}`;
        const applyId = `apply_filter_${timestamp}`;
        const clearId = `clear_filter_${timestamp}`;

        // Get default date range (current month)
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Create filter container
        const filterDiv = document.createElement('div');
        filterDiv.className = 'sale_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="sale_date_filter_container">
                <div class="date_filter_wrapper">
                    <label class="date_label">Order Date:</label>
                    <div class="date_input_group">
                        <input
                            type="date"
                            class="form-control date_input"
                            id="${fromId}"
                            value="${dateFrom}"
                        />
                        <span class="date_separator">→</span>
                        <input
                            type="date"
                            class="form-control date_input"
                            id="${toId}"
                            value="${dateTo}"
                        />
                    </div>
                    <button class="btn btn-primary apply_filter_btn" id="${applyId}">
                        Apply Filter
                    </button>
                    <button class="btn btn-secondary clear_filter_btn" id="${clearId}">
                        Clear
                    </button>
                </div>
            </div>
        `;

        // Insert into DOM
        listView.parentElement.insertBefore(filterDiv, listView);
        this._filterElement = filterDiv;

        // Attach event listeners
        this.attachFilterEvents(fromId, toId, applyId, clearId);
    },

    attachFilterEvents(fromId, toId, applyId, clearId) {
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const applyBtn = document.getElementById(applyId);
        const clearBtn = document.getElementById(clearId);

        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) return;

        applyBtn.addEventListener('click', () => {
            const dateFrom = dateFromInput.value;
            const dateTo = dateToInput.value;

            if (!dateFrom || !dateTo) {
                this.notification.add("Please select both dates", { type: "warning" });
                return;
            }

            if (dateFrom > dateTo) {
                this.notification.add("Start date must be before end date", { type: "warning" });
                return;
            }

            // Build domain with date filter + sale order state
            const domain = [
                ['date_order', '>=', dateFrom + ' 00:00:00'],
                ['date_order', '<=', dateTo + ' 23:59:59'],
                ['state', 'in', ['sale', 'done']]
            ];

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Sale Orders',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });

            this.notification.add("Date filter applied", { type: "success" });
        });

        clearBtn.addEventListener('click', () => {
            // Reset dates to current month
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            dateFromInput.value = firstDay.toISOString().split('T')[0];
            dateToInput.value = today.toISOString().split('T')[0];

            // Reload with default domain
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Sale Orders',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [['state', 'in', ['sale', 'done']]],
                target: 'current',
            });

            this.notification.add("Filter cleared", { type: "info" });
        });
    },
});