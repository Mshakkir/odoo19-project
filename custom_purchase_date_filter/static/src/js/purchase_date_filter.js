/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for Purchase Orders and Bills
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
            purchaseReps: []
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

        // Check if it's Purchase Orders
        if (resModel === 'purchase.order') {
            const action = this.env.config;

            if (action.xmlId === 'purchase.purchase_rfq' ||
                action.xmlId === 'purchase.purchase_form_action') {
                return true;
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('purchase') && actionName.includes('order')) {
                    return true;
                }
            }

            if (this.props.domain) {
                const hasOrderState = this.props.domain.some(item =>
                    Array.isArray(item) &&
                    item[0] === 'state' &&
                    (JSON.stringify(item).includes('purchase') || JSON.stringify(item).includes('done'))
                );
                if (hasOrderState) {
                    return true;
                }
            }
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
            // Load warehouses
            const warehouses = await this.orm.searchRead(
                'stock.warehouse',
                [],
                ['id', 'name'],
                { limit: 100 }
            );

            // Load vendors (partners that are suppliers)
            const vendors = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load purchase representatives (users)
            const purchaseReps = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            this._purchaseFilterData = {
                warehouses: warehouses,
                vendors: vendors,
                purchaseReps: purchaseReps
            };

            this.injectPurchaseDateFilter();
        } catch (error) {
            console.error('Error loading purchase filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    injectPurchaseDateFilter() {
        this.cleanupPurchaseFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectPurchaseDateFilter(), 100);
            return;
        }

        if (document.querySelector('.purchase_date_filter_wrapper_main')) {
            return;
        }

        const timestamp = Date.now();
        const fromId = `purchase_date_from_${timestamp}`;
        const toId = `purchase_date_to_${timestamp}`;
        const warehouseId = `purchase_warehouse_${timestamp}`;
        const vendorId = `purchase_vendor_${timestamp}`;
        const repId = `purchase_rep_${timestamp}`;
        const orderRefId = `purchase_order_ref_${timestamp}`;
        const vendorRefId = `purchase_vendor_ref_${timestamp}`;
        const shippingRefId = `purchase_shipping_ref_${timestamp}`;
        const amountFromId = `purchase_amount_from_${timestamp}`;
        const amountToId = `purchase_amount_to_${timestamp}`;
        const billingStatusId = `purchase_billing_status_${timestamp}`;
        const applyId = `purchase_apply_${timestamp}`;
        const clearId = `purchase_clear_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Determine if this is Purchase Orders or Bills
        const isPurchaseOrder = this.props.resModel === 'purchase.order';
        const isBill = this.props.resModel === 'account.move';

        // Set labels based on model
        const dateLabel = isPurchaseOrder ? 'Order Date:' : 'Bill Date:';
        const vendorLabel = 'Vendor:';
        const repLabel = isPurchaseOrder ? 'Purchase Rep:' : 'Purchase Rep:';
        const actionName = isPurchaseOrder ? 'Purchase Orders' : 'Vendor Bills';

        // Build options for warehouse dropdown
        const warehouseOptions = this._purchaseFilterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        const filterDiv = document.createElement('div');
        filterDiv.className = 'purchase_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="purchase_date_filter_container">
                <!-- Row 1: Date, Warehouse, Vendor, Purchase Rep -->
                <div class="date_filter_wrapper">
                    <!-- Date Range Filter -->
                    <div class="filter_group date_group">
                        <label class="filter_label">${dateLabel}</label>
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" />
                        </div>
                    </div>

                    <!-- Warehouse Filter (Normal Dropdown) -->
                    <div class="filter_group">
                        <label class="filter_label">Warehouse:</label>
                        <select class="form-select filter_select" id="${warehouseId}">
                            <option value="">All</option>
                            ${warehouseOptions}
                        </select>
                    </div>

                    <!-- Vendor Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">${vendorLabel}</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${vendorId}_input"
                                placeholder="All Vendors"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${vendorId}_value" />
                            <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Purchase Rep Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">${repLabel}</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${repId}_input"
                                placeholder="All Reps"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${repId}_value" />
                            <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
                        </div>
                    </div>
                </div>

                <!-- Row 2: Order Reference, Vendor Reference, Shipping Reference, Amount, Billing Status, Actions -->
                <div class="date_filter_wrapper" style="margin-top: 10px;">
                    <!-- Order Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Order Ref:</label>
                        <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="PO..." />
                    </div>

                    <!-- Vendor Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Vendor Ref:</label>
                        <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
                    </div>

                    <!-- Shipping Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Shipping Ref:</label>
                        <input type="text" class="form-control filter_input" id="${shippingRefId}" placeholder="AWB..." />
                    </div>

                    <!-- Total Amount Range Filter -->
                    <div class="filter_group amount_group">
                        <label class="filter_label">Total Amount:</label>
                        <div class="amount_input_group">
                            <input type="number" class="form-control amount_input" id="${amountFromId}" placeholder="Min" step="0.01" />
                            <span class="date_separator">→</span>
                            <input type="number" class="form-control amount_input" id="${amountToId}" placeholder="Max" step="0.01" />
                        </div>
                    </div>

                    <!-- Billing Status Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Billing Status:</label>
                        <select class="form-select filter_select" id="${billingStatusId}">
                            <option value="">All</option>
                            <option value="no">Nothing to Bill</option>
                            <option value="to invoice">To Invoice</option>
                            <option value="invoiced">Fully Invoiced</option>
                        </select>
                    </div>

                    <!-- Action Buttons -->
                    <div class="filter_actions">
                        <button class="btn btn-primary apply_filter_btn" id="${applyId}">Apply</button>
                        <button class="btn btn-secondary clear_filter_btn" id="${clearId}">Clear</button>
                    </div>
                </div>
            </div>
        `;

        listTable.parentElement.insertBefore(filterDiv, listTable);
        this._purchaseFilterElement = filterDiv;

        // Setup autocomplete
        this.setupPurchaseAutocomplete(vendorId, this._purchaseFilterData.vendors);
        this.setupPurchaseAutocomplete(repId, this._purchaseFilterData.purchaseReps);

        this.attachPurchaseFilterEvents(
            fromId, toId, warehouseId, vendorId, repId,
            orderRefId, vendorRefId, shippingRefId, amountFromId, amountToId, billingStatusId,
            applyId, clearId, actionName, isPurchaseOrder, isBill
        );
    },

    setupPurchaseAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        input.addEventListener('focus', () => {
            this.filterPurchaseAutocomplete(fieldId, dataList, '');
            dropdown.classList.add('show');
        });

        input.addEventListener('input', (e) => {
            const searchTerm = e.target.value;
            hiddenValue.value = '';
            this.filterPurchaseAutocomplete(fieldId, dataList, searchTerm);
            dropdown.classList.add('show');
        });

        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    },

    filterPurchaseAutocomplete(fieldId, dataList, searchTerm) {
        const dropdown = document.getElementById(`${fieldId}_dropdown`);
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);

        if (!dropdown) return;

        const lowerSearch = searchTerm.toLowerCase();
        const filtered = dataList.filter(item =>
            item.name.toLowerCase().includes(lowerSearch)
        );

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No results found</div>';
            return;
        }

        dropdown.innerHTML = filtered.map(item => `
            <div class="autocomplete_item" data-id="${item.id}" data-name="${item.name}">
                ${item.name}
            </div>
        `).join('');

        dropdown.querySelectorAll('.autocomplete_item:not(.no_results)').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.getAttribute('data-id');
                const name = item.getAttribute('data-name');
                input.value = name;
                hiddenValue.value = id;
                dropdown.classList.remove('show');
            });
        });
    },

    attachPurchaseFilterEvents(
        fromId, toId, warehouseId, vendorId, repId,
        orderRefId, vendorRefId, shippingRefId, amountFromId, amountToId, billingStatusId,
        applyId, clearId, actionName, isPurchaseOrder, isBill
    ) {
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const warehouseSelect = document.getElementById(warehouseId);
        const vendorValue = document.getElementById(`${vendorId}_value`);
        const vendorInput = document.getElementById(`${vendorId}_input`);
        const repValue = document.getElementById(`${repId}_value`);
        const repInput = document.getElementById(`${repId}_input`);
        const orderRefInput = document.getElementById(orderRefId);
        const vendorRefInput = document.getElementById(vendorRefId);
        const shippingRefInput = document.getElementById(shippingRefId);
        const amountFromInput = document.getElementById(amountFromId);
        const amountToInput = document.getElementById(amountToId);
        const billingStatusSelect = document.getElementById(billingStatusId);
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

            let domain = [];
            let resModel = '';
            let views = [];

            if (isPurchaseOrder) {
                domain = [
                    ['date_order', '>=', dateFrom + ' 00:00:00'],
                    ['date_order', '<=', dateTo + ' 23:59:59'],
                    ['state', 'in', ['purchase', 'done']]
                ];
                resModel = 'purchase.order';
                views = [[false, 'list'], [false, 'form']];
            } else if (isBill) {
                domain = [
                    ['invoice_date', '>=', dateFrom],
                    ['invoice_date', '<=', dateTo],
                    ['move_type', '=', 'in_invoice'],
                    ['state', '!=', 'cancel']
                ];
                resModel = 'account.move';
                views = [[false, 'list'], [false, 'form']];
            }

            // Add warehouse filter (only for purchase orders)
            if (warehouseSelect.value && isPurchaseOrder) {
                domain.push(['picking_type_id.warehouse_id', '=', parseInt(warehouseSelect.value)]);
            }

            // Add vendor filter
            if (vendorValue.value) {
                domain.push(['partner_id', '=', parseInt(vendorValue.value)]);
            }

            // Add purchase rep filter
            if (repValue.value) {
                domain.push(['user_id', '=', parseInt(repValue.value)]);
            }

            // Add order reference filter
            if (orderRefInput.value.trim()) {
                domain.push(['name', 'ilike', orderRefInput.value.trim()]);
            }

            // Add vendor reference filter
            if (vendorRefInput.value.trim()) {
                domain.push(['partner_ref', 'ilike', vendorRefInput.value.trim()]);
            }

            // Add shipping reference filter (awb_number)
            if (shippingRefInput.value.trim() && isPurchaseOrder) {
                domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
            }

            // Add amount range filter
            if (amountFromInput.value) {
                domain.push(['amount_total', '>=', parseFloat(amountFromInput.value)]);
            }
            if (amountToInput.value) {
                domain.push(['amount_total', '<=', parseFloat(amountToInput.value)]);
            }

            // Add billing status filter (only for purchase orders)
            if (billingStatusSelect.value && isPurchaseOrder) {
                domain.push(['invoice_status', '=', billingStatusSelect.value]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: actionName,
                res_model: resModel,
                views: views,
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters applied", { type: "success" });
        });

        clearBtn.addEventListener('click', () => {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            dateFromInput.value = firstDay.toISOString().split('T')[0];
            dateToInput.value = today.toISOString().split('T')[0];
            warehouseSelect.value = '';
            vendorInput.value = '';
            vendorValue.value = '';
            repInput.value = '';
            repValue.value = '';
            orderRefInput.value = '';
            vendorRefInput.value = '';
            shippingRefInput.value = '';
            amountFromInput.value = '';
            amountToInput.value = '';
            billingStatusSelect.value = '';

            let domain = [];
            let resModel = '';
            let views = [];

            if (isPurchaseOrder) {
                domain = [['state', 'in', ['purchase', 'done']]];
                resModel = 'purchase.order';
                views = [[false, 'list'], [false, 'form']];
            } else if (isBill) {
                domain = [['move_type', '=', 'in_invoice']];
                resModel = 'account.move';
                views = [[false, 'list'], [false, 'form']];
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: actionName,
                res_model: resModel,
                views: views,
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        });
    },
});















///** @odoo-module **/
//
//import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//
//// Patch ListController to inject date filter for Purchase Orders and Bills
//patch(ListController.prototype, {
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this.actionService = useService("action");
//        this.orm = useService("orm");
//        this._purchaseFilterElement = null;
//        this._purchaseFilterData = {
//            warehouses: [],
//            vendors: [],
//            purchaseReps: []
//        };
//
//        onMounted(() => {
//            if (this.shouldShowPurchaseFilter()) {
//                setTimeout(() => this.loadPurchaseFilterData(), 150);
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupPurchaseFilter();
//        });
//    },
//
//    shouldShowPurchaseFilter() {
//        const resModel = this.props.resModel;
//
//        // Check if it's Purchase Orders
//        if (resModel === 'purchase.order') {
//            const action = this.env.config;
//
//            if (action.xmlId === 'purchase.purchase_rfq' ||
//                action.xmlId === 'purchase.purchase_form_action') {
//                return true;
//            }
//
//            if (action.displayName || action.name) {
//                const actionName = (action.displayName || action.name).toLowerCase();
//                if (actionName.includes('purchase') && actionName.includes('order')) {
//                    return true;
//                }
//            }
//
//            if (this.props.domain) {
//                const hasOrderState = this.props.domain.some(item =>
//                    Array.isArray(item) &&
//                    item[0] === 'state' &&
//                    (JSON.stringify(item).includes('purchase') || JSON.stringify(item).includes('done'))
//                );
//                if (hasOrderState) {
//                    return true;
//                }
//            }
//        }
//
//        // Check if it's Vendor Bills (account.move with in_invoice)
//        if (resModel === 'account.move') {
//            const action = this.env.config;
//
//            if (action.xmlId === 'account.action_move_in_invoice_type' ||
//                action.xmlId === 'purchase.action_vendor_bill_template') {
//                return true;
//            }
//
//            if (action.displayName || action.name) {
//                const actionName = (action.displayName || action.name).toLowerCase();
//                if (actionName.includes('bill') ||
//                    (actionName.includes('vendor') && actionName.includes('invoice'))) {
//                    return true;
//                }
//            }
//
//            if (this.props.domain) {
//                const domainStr = JSON.stringify(this.props.domain);
//                if (domainStr.includes('move_type') &&
//                    domainStr.includes('in_invoice')) {
//                    return true;
//                }
//            }
//        }
//
//        return false;
//    },
//
//    cleanupPurchaseFilter() {
//        if (this._purchaseFilterElement && this._purchaseFilterElement.parentNode) {
//            this._purchaseFilterElement.remove();
//            this._purchaseFilterElement = null;
//        }
//    },
//
//    async loadPurchaseFilterData() {
//        try {
//            // Load warehouses
//            const warehouses = await this.orm.searchRead(
//                'stock.warehouse',
//                [],
//                ['id', 'name'],
//                { limit: 100 }
//            );
//
//            // Load vendors (partners that are suppliers)
//            const vendors = await this.orm.searchRead(
//                'res.partner',
//                [['supplier_rank', '>', 0]],
//                ['id', 'name'],
//                { limit: 500, order: 'name' }
//            );
//
//            // Load purchase representatives (users)
//            const purchaseReps = await this.orm.searchRead(
//                'res.users',
//                [],
//                ['id', 'name'],
//                { limit: 100, order: 'name' }
//            );
//
//            this._purchaseFilterData = {
//                warehouses: warehouses,
//                vendors: vendors,
//                purchaseReps: purchaseReps
//            };
//
//            this.injectPurchaseDateFilter();
//        } catch (error) {
//            console.error('Error loading purchase filter data:', error);
//            this.notification.add("Error loading filter options", { type: "danger" });
//        }
//    },
//
//    injectPurchaseDateFilter() {
//        this.cleanupPurchaseFilter();
//
//        const listTable = document.querySelector('.o_list_table');
//
//        if (!listTable) {
//            setTimeout(() => this.injectPurchaseDateFilter(), 100);
//            return;
//        }
//
//        if (document.querySelector('.purchase_date_filter_wrapper_main')) {
//            return;
//        }
//
//        const timestamp = Date.now();
//        const fromId = `purchase_date_from_${timestamp}`;
//        const toId = `purchase_date_to_${timestamp}`;
//        const warehouseId = `purchase_warehouse_${timestamp}`;
//        const vendorId = `purchase_vendor_${timestamp}`;
//        const repId = `purchase_rep_${timestamp}`;
//        const applyId = `purchase_apply_${timestamp}`;
//        const clearId = `purchase_clear_${timestamp}`;
//
//        const today = new Date();
//        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//        const dateFrom = firstDay.toISOString().split('T')[0];
//        const dateTo = today.toISOString().split('T')[0];
//
//        // Determine if this is Purchase Orders or Bills
//        const isPurchaseOrder = this.props.resModel === 'purchase.order';
//        const isBill = this.props.resModel === 'account.move';
//
//        // Set labels based on model
//        const dateLabel = isPurchaseOrder ? 'Order Date:' : 'Bill Date:';
//        const vendorLabel = 'Vendor:';
//        const repLabel = isPurchaseOrder ? 'Purchase Rep:' : 'Purchase Rep:';
//        const actionName = isPurchaseOrder ? 'Purchase Orders' : 'Vendor Bills';
//
//        // Build options for warehouse dropdown
//        const warehouseOptions = this._purchaseFilterData.warehouses
//            .map(w => `<option value="${w.id}">${w.name}</option>`)
//            .join('');
//
//        const filterDiv = document.createElement('div');
//        filterDiv.className = 'purchase_date_filter_wrapper_main';
//        filterDiv.innerHTML = `
//            <div class="purchase_date_filter_container">
//                <div class="date_filter_wrapper">
//                    <!-- Date Range Filter -->
//                    <div class="filter_group date_group">
//                        <label class="filter_label">${dateLabel}</label>
//                        <div class="date_input_group">
//                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" />
//                            <span class="date_separator">→</span>
//                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" />
//                        </div>
//                    </div>
//
//                    <!-- Warehouse Filter (Normal Dropdown) -->
//                    <div class="filter_group">
//                        <label class="filter_label">Warehouse:</label>
//                        <select class="form-select filter_select" id="${warehouseId}">
//                            <option value="">All</option>
//                            ${warehouseOptions}
//                        </select>
//                    </div>
//
//                    <!-- Vendor Filter (Searchable) -->
//                    <div class="filter_group autocomplete_group">
//                        <label class="filter_label">${vendorLabel}</label>
//                        <div class="autocomplete_wrapper">
//                            <input
//                                type="text"
//                                class="form-control autocomplete_input"
//                                id="${vendorId}_input"
//                                placeholder="All Vendors"
//                                autocomplete="off"
//                            />
//                            <input type="hidden" id="${vendorId}_value" />
//                            <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
//                        </div>
//                    </div>
//
//                    <!-- Purchase Rep Filter (Searchable) -->
//                    <div class="filter_group autocomplete_group">
//                        <label class="filter_label">${repLabel}</label>
//                        <div class="autocomplete_wrapper">
//                            <input
//                                type="text"
//                                class="form-control autocomplete_input"
//                                id="${repId}_input"
//                                placeholder="All Reps"
//                                autocomplete="off"
//                            />
//                            <input type="hidden" id="${repId}_value" />
//                            <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
//                        </div>
//                    </div>
//
//                    <!-- Action Buttons -->
//                    <div class="filter_actions">
//                        <button class="btn btn-primary apply_filter_btn" id="${applyId}">Apply</button>
//                        <button class="btn btn-secondary clear_filter_btn" id="${clearId}">Clear</button>
//                    </div>
//                </div>
//            </div>
//        `;
//
//        listTable.parentElement.insertBefore(filterDiv, listTable);
//        this._purchaseFilterElement = filterDiv;
//
//        // Setup autocomplete
//        this.setupPurchaseAutocomplete(vendorId, this._purchaseFilterData.vendors);
//        this.setupPurchaseAutocomplete(repId, this._purchaseFilterData.purchaseReps);
//
//        this.attachPurchaseFilterEvents(fromId, toId, warehouseId, vendorId, repId, applyId, clearId, actionName, isPurchaseOrder, isBill);
//    },
//
//    setupPurchaseAutocomplete(fieldId, dataList) {
//        const input = document.getElementById(`${fieldId}_input`);
//        const hiddenValue = document.getElementById(`${fieldId}_value`);
//        const dropdown = document.getElementById(`${fieldId}_dropdown`);
//
//        if (!input || !dropdown || !hiddenValue) return;
//
//        input.addEventListener('focus', () => {
//            this.filterPurchaseAutocomplete(fieldId, dataList, '');
//            dropdown.classList.add('show');
//        });
//
//        input.addEventListener('input', (e) => {
//            const searchTerm = e.target.value;
//            hiddenValue.value = '';
//            this.filterPurchaseAutocomplete(fieldId, dataList, searchTerm);
//            dropdown.classList.add('show');
//        });
//
//        document.addEventListener('click', (e) => {
//            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
//                dropdown.classList.remove('show');
//            }
//        });
//    },
//
//    filterPurchaseAutocomplete(fieldId, dataList, searchTerm) {
//        const dropdown = document.getElementById(`${fieldId}_dropdown`);
//        const input = document.getElementById(`${fieldId}_input`);
//        const hiddenValue = document.getElementById(`${fieldId}_value`);
//
//        if (!dropdown) return;
//
//        const lowerSearch = searchTerm.toLowerCase();
//        const filtered = dataList.filter(item =>
//            item.name.toLowerCase().includes(lowerSearch)
//        );
//
//        if (filtered.length === 0) {
//            dropdown.innerHTML = '<div class="autocomplete_item no_results">No results found</div>';
//            return;
//        }
//
//        dropdown.innerHTML = filtered.map(item => `
//            <div class="autocomplete_item" data-id="${item.id}" data-name="${item.name}">
//                ${item.name}
//            </div>
//        `).join('');
//
//        dropdown.querySelectorAll('.autocomplete_item:not(.no_results)').forEach(item => {
//            item.addEventListener('click', () => {
//                const id = item.getAttribute('data-id');
//                const name = item.getAttribute('data-name');
//                input.value = name;
//                hiddenValue.value = id;
//                dropdown.classList.remove('show');
//            });
//        });
//    },
//
//    attachPurchaseFilterEvents(fromId, toId, warehouseId, vendorId, repId, applyId, clearId, actionName, isPurchaseOrder, isBill) {
//        const dateFromInput = document.getElementById(fromId);
//        const dateToInput = document.getElementById(toId);
//        const warehouseSelect = document.getElementById(warehouseId);
//        const vendorValue = document.getElementById(`${vendorId}_value`);
//        const vendorInput = document.getElementById(`${vendorId}_input`);
//        const repValue = document.getElementById(`${repId}_value`);
//        const repInput = document.getElementById(`${repId}_input`);
//        const applyBtn = document.getElementById(applyId);
//        const clearBtn = document.getElementById(clearId);
//
//        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) return;
//
//        applyBtn.addEventListener('click', () => {
//            const dateFrom = dateFromInput.value;
//            const dateTo = dateToInput.value;
//
//            if (!dateFrom || !dateTo) {
//                this.notification.add("Please select both dates", { type: "warning" });
//                return;
//            }
//
//            if (dateFrom > dateTo) {
//                this.notification.add("Start date must be before end date", { type: "warning" });
//                return;
//            }
//
//            let domain = [];
//            let resModel = '';
//            let views = [];
//
//            if (isPurchaseOrder) {
//                domain = [
//                    ['date_order', '>=', dateFrom + ' 00:00:00'],
//                    ['date_order', '<=', dateTo + ' 23:59:59'],
//                    ['state', 'in', ['purchase', 'done']]
//                ];
//                resModel = 'purchase.order';
//                views = [[false, 'list'], [false, 'form']];
//            } else if (isBill) {
//                domain = [
//                    ['invoice_date', '>=', dateFrom],
//                    ['invoice_date', '<=', dateTo],
//                    ['move_type', '=', 'in_invoice'],
//                    ['state', '!=', 'cancel']
//                ];
//                resModel = 'account.move';
//                views = [[false, 'list'], [false, 'form']];
//            }
//
//            // Add warehouse filter (only for purchase orders)
//            if (warehouseSelect.value && isPurchaseOrder) {
//                domain.push(['picking_type_id.warehouse_id', '=', parseInt(warehouseSelect.value)]);
//            }
//
//            // Add vendor filter
//            if (vendorValue.value) {
//                domain.push(['partner_id', '=', parseInt(vendorValue.value)]);
//            }
//
//            // Add purchase rep filter
//            if (repValue.value) {
//                domain.push(['user_id', '=', parseInt(repValue.value)]);
//            }
//
//            this.actionService.doAction({
//                type: 'ir.actions.act_window',
//                name: actionName,
//                res_model: resModel,
//                views: views,
//                domain: domain,
//                target: 'current',
//            });
//
//            this.notification.add("Filters applied", { type: "success" });
//        });
//
//        clearBtn.addEventListener('click', () => {
//            const today = new Date();
//            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//            dateFromInput.value = firstDay.toISOString().split('T')[0];
//            dateToInput.value = today.toISOString().split('T')[0];
//            warehouseSelect.value = '';
//            vendorInput.value = '';
//            vendorValue.value = '';
//            repInput.value = '';
//            repValue.value = '';
//
//            let domain = [];
//            let resModel = '';
//            let views = [];
//
//            if (isPurchaseOrder) {
//                domain = [['state', 'in', ['purchase', 'done']]];
//                resModel = 'purchase.order';
//                views = [[false, 'list'], [false, 'form']];
//            } else if (isBill) {
//                domain = [['move_type', '=', 'in_invoice']];
//                resModel = 'account.move';
//                views = [[false, 'list'], [false, 'form']];
//            }
//
//            this.actionService.doAction({
//                type: 'ir.actions.act_window',
//                name: actionName,
//                res_model: resModel,
//                views: views,
//                domain: domain,
//                target: 'current',
//            });
//
//            this.notification.add("Filters cleared", { type: "info" });
//        });
//    },
//});