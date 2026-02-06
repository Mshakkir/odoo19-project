/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for Purchase Orders, RFQs and Bills
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this._purchaseFilterElement = null;
        this._purchaseFilterData = {
            warehouses: [],
            vendors: [],
            purchaseReps: [],
            analyticAccounts: []  // Added analytic accounts
        };

        onMounted(() => {
            if (this.shouldShowPurchaseFilter()) {
                setTimeout(() => this.loadPurchaseFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupPurchaseFilter();
        });
    },

    shouldShowPurchaseFilter() {
        const resModel = this.props.resModel;

        // Check if it's Purchase Orders or RFQs
        if (resModel === 'purchase.order') {
            const action = this.env.config;

            // RFQ action
            if (action.xmlId === 'purchase.purchase_rfq') {
                return true;
            }

            // Purchase Order action
            if (action.xmlId === 'purchase.purchase_form_action') {
                return true;
            }

            // Check action name
            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('purchase') || actionName.includes('rfq') || actionName.includes('request for quotation')) {
                    return true;
                }
            }

            // Check domain for purchase states
            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('state') &&
                    (domainStr.includes('purchase') || domainStr.includes('done') ||
                     domainStr.includes('draft') || domainStr.includes('sent'))) {
                    return true;
                }
            }

            return true; // Show for all purchase.order views
        }

        // Check if it's Vendor Bills (account.move with in_invoice)
        if (resModel === 'account.move') {
            const action = this.env.config;

            if (action.xmlId === 'account.action_move_in_invoice_type' ||
                action.xmlId === 'purchase.action_vendor_bill_template') {
                return true;
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('bill') ||
                    (actionName.includes('vendor') && actionName.includes('invoice'))) {
                    return true;
                }
            }

            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('move_type') &&
                    domainStr.includes('in_invoice')) {
                    return true;
                }
            }
        }

        return false;
    },

    cleanupPurchaseFilter() {
        if (this._purchaseFilterElement && this._purchaseFilterElement.parentNode) {
            this._purchaseFilterElement.remove();
            this._purchaseFilterElement = null;
        }
    },

    async loadPurchaseFilterData() {
        try {
            // Load warehouses, vendors, purchase reps, and analytic accounts
            const [warehouses, vendors, purchaseReps, analyticAccounts] = await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }),
                this.orm.searchRead('res.partner', [['supplier_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }),
                this.orm.searchRead('account.analytic.account', [], ['id', 'name', 'code'],
                    { limit: 500, order: 'name' })
            ]);

            this._purchaseFilterData = {
                warehouses: warehouses || [],
                vendors: vendors || [],
                purchaseReps: purchaseReps || [],
                analyticAccounts: analyticAccounts || []
            };

            this.injectPurchaseDateFilter();
        } catch (error) {
            console.error('Error loading purchase filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    getViewType() {
        const resModel = this.props.resModel;
        const action = this.env.config;

        // Check RFQ
        if (resModel === 'purchase.order') {
            if (action.xmlId === 'purchase.purchase_rfq') {
                return 'rfq';
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('rfq') || actionName.includes('request for quotation')) {
                    return 'rfq';
                }
            }

            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('draft') || domainStr.includes('sent')) {
                    return 'rfq';
                }
            }
        }

        if (resModel === 'account.move') {
            return 'bill';
        }

        return 'purchase_order';
    },

    showVendorDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.vendors;
        } else {
            filtered = this._purchaseFilterData.vendors.filter(v =>
                (v.name && typeof v.name === 'string') ? v.name.toLowerCase().includes(lowerSearch) : false
            );
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No vendors found</div>';
        } else {
            dropdown.innerHTML = filtered.map(v =>
                `<div class="autocomplete_item" data-id="${v.id}">${v.name || ''}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },

    showPurchaseRepDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.purchaseReps;
        } else {
            filtered = this._purchaseFilterData.purchaseReps.filter(r =>
                (r.name && typeof r.name === 'string') ? r.name.toLowerCase().includes(lowerSearch) : false
            );
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No users found</div>';
        } else {
            dropdown.innerHTML = filtered.map(r =>
                `<div class="autocomplete_item" data-id="${r.id}">${r.name || ''}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },

    showAnalyticDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.analyticAccounts;
        } else {
            filtered = this._purchaseFilterData.analyticAccounts.filter(a => {
                const nameMatch = (a.name && typeof a.name === 'string') ? a.name.toLowerCase().includes(lowerSearch) : false;
                const codeMatch = (a.code && typeof a.code === 'string') ? a.code.toLowerCase().includes(lowerSearch) : false;
                return nameMatch || codeMatch;
            });
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No analytic accounts found</div>';
        } else {
            dropdown.innerHTML = filtered.map(a => {
                const displayText = a.code ? `${a.code} - ${a.name || ''}` : (a.name || 'Unnamed');
                return `<div class="autocomplete_item" data-id="${a.id}" data-code="${a.code || ''}" data-name="${a.name || ''}">${displayText}</div>`;
            }).join('');
        }

        dropdown.classList.add('show');
    },
});