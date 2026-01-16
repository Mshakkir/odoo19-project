/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for RFQ
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this._rfqFilterElement = null;
        this._rfqFilterData = {
            warehouses: [],
            vendors: [],
            purchaseReps: []
        };

        onMounted(() => {
            if (this.shouldShowRFQFilter()) {
                setTimeout(() => this.loadRFQFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupRFQFilter();
        });
    },

    shouldShowRFQFilter() {
        const resModel = this.props.resModel;

        // Check if it's RFQ/Quotations (draft/sent state)
        if (resModel === 'purchase.order') {
            const action = this.env.config;

            // Check for RFQ action
            if (action.xmlId === 'purchase.purchase_rfq') {
                return true;
            }

            // Check action name
            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('rfq') || actionName.includes('request for quotation')) {
                    return true;
                }
            }

            // Check domain for RFQ states
            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('draft') || domainStr.includes('sent')) {
                    const hasRFQState = this.props.domain.some(item =>
                        Array.isArray(item) &&
                        item[0] === 'state' &&
                        (JSON.stringify(item).includes('draft') || JSON.stringify(item).includes('sent'))
                    );
                    if (hasRFQState) {
                        return true;
                    }
                }
            }
        }

        return false;
    },

    cleanupRFQFilter() {
        if (this._rfqFilterElement && this._rfqFilterElement.parentNode) {
            this._rfqFilterElement.remove();
            this._rfqFilterElement = null;
        }
    },

    async loadRFQFilterData() {
        try {
            // Load warehouses
            const warehouses = await this.orm.searchRead(
                'stock.warehouse',
                [],
                ['id', 'name'],
                { limit: 100 }
            );

            // Load vendors
            const vendors = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load purchase representatives
            const purchaseReps = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            this._rfqFilterData = {
                warehouses: warehouses,
                vendors: vendors,
                purchaseReps: purchaseReps
            };

            this.injectRFQDateFilter();
        } catch (error) {
            console.error('Error loading RFQ filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    injectRFQDateFilter() {
        this.cleanupRFQFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectRFQDateFilter(), 100);
            return;
        }

        if (document.querySelector('.rfq_date_filter_wrapper_main')) {
            return;
        }

        const timestamp = Date.now();
        const fromId = `rfq_date_from_${timestamp}`;
        const toId = `rfq_date_to_${timestamp}`;
        const warehouseId = `rfq_warehouse_${timestamp}`;
        const vendorId = `rfq_vendor_${timestamp}`;
        const repId = `rfq_rep_${timestamp}`;
        const orderRefId = `rfq_order_ref_${timestamp}`;
        const vendorRefId = `rfq_vendor_ref_${timestamp}`;
        const shippingRefId = `rfq_shipping_ref_${timestamp}`;
        const amountId = `rfq_amount_${timestamp}`;
        const statusId = `rfq_status_${timestamp}`;
        const applyId = `rfq_apply_${timestamp}`;
        const clearId = `rfq_clear_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Build options for warehouse dropdown
        const warehouseOptions = this._rfqFilterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        const filterDiv = document.createElement('div');
        filterDiv.className = 'rfq_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="rfq_date_filter_container">
                <div class="date_filter_wrapper">
                    <!-- Date Range Filter -->
                    <div class="filter_group date_group">
                        <label class="filter_label">Order Date:</label>
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
                        </div>
                    </div>

                    <!-- Order Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Order Ref:</label>
                        <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="RFQ..." />
                    </div>

                    <!-- Vendor Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">Vendor:</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${vendorId}_input"
                                placeholder="Vendor"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${vendorId}_value" />
                            <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Vendor Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Vendor Ref:</label>
                        <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
                    </div>

                    <!-- Warehouse Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Warehouse:</label>
                        <select class="form-select filter_select" id="${warehouseId}">
                            <option value="">Warehouse</option>
                            ${warehouseOptions}
                        </select>
                    </div>

                    <!-- Shipping Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Shipping Ref:</label>
                        <input type="text" class="form-control filter_input" id="${shippingRefId}" placeholder="AWB..." />
                    </div>

                    <!-- Total Amount Filter -->
                    <div class="filter_group amount_group">
                        <label class="filter_label">Amount:</label>
                        <input type="number" class="form-control amount_input" id="${amountId}" placeholder="Total Amount" step="0.01" />
                    </div>

                    <!-- Purchase Rep Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">Purchase Rep:</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${repId}_input"
                                placeholder="Purchase Rep"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${repId}_value" />
                            <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Status Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Status:</label>
                        <select class="form-select filter_select" id="${statusId}">
                            <option value="">Status</option>
                            <option value="draft">Draft</option>
                            <option value="sent">RFQ Sent</option>
                            <option value="to approve">To Approve</option>
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
        this._rfqFilterElement = filterDiv;

        // Setup autocomplete
        this.setupRFQAutocomplete(vendorId, this._rfqFilterData.vendors);
        this.setupRFQAutocomplete(repId, this._rfqFilterData.purchaseReps);

        this.attachRFQFilterEvents(
            fromId, toId, warehouseId, vendorId, repId,
            orderRefId, vendorRefId, shippingRefId, amountId, statusId,
            applyId, clearId
        );
    },

    setupRFQAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        input.addEventListener('focus', () => {
            this.filterRFQAutocomplete(fieldId, dataList, '');
            dropdown.classList.add('show');
        });

        input.addEventListener('input', (e) => {
            const searchTerm = e.target.value;
            hiddenValue.value = '';
            this.filterRFQAutocomplete(fieldId, dataList, searchTerm);
            dropdown.classList.add('show');
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                dropdown.classList.remove('show');
                const applyBtn = document.querySelector('.apply_filter_btn');
                if (applyBtn) {
                    applyBtn.click();
                }
            }
        });

        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    },

    filterRFQAutocomplete(fieldId, dataList, searchTerm) {
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

    attachRFQFilterEvents(
        fromId, toId, warehouseId, vendorId, repId,
        orderRefId, vendorRefId, shippingRefId, amountId, statusId,
        applyId, clearId
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
        const amountInput = document.getElementById(amountId);
        const statusSelect = document.getElementById(statusId);
        const applyBtn = document.getElementById(applyId);
        const clearBtn = document.getElementById(clearId);

        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) return;

        // Apply filter function
        const applyFilter = () => {
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

            let domain = [
                ['date_order', '>=', dateFrom + ' 00:00:00'],
                ['date_order', '<=', dateTo + ' 23:59:59'],
                ['state', 'in', ['draft', 'sent', 'to approve']]
            ];

            // Add warehouse filter
            if (warehouseSelect.value) {
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

            // Add shipping reference filter
            if (shippingRefInput.value.trim()) {
                domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
            }

            // Add amount filter
            if (amountInput.value) {
                const exactAmount = parseFloat(amountInput.value);
                domain.push(['amount_total', '=', exactAmount]);
            }

            // Add status filter
            if (statusSelect.value) {
                domain.push(['state', '=', statusSelect.value]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Request for Quotation',
                res_model: 'purchase.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                context: {
                    'tree_view_ref': 'custom_purchase_rfq_list.purchase_order_tree_inherit_custom'
                },
                target: 'current',
            });

            this.notification.add("Filters applied", { type: "success" });
        };

        // Click on Apply button
        applyBtn.addEventListener('click', applyFilter);

        // Press Enter on any input field to apply filter
        const allInputs = [
            dateFromInput, dateToInput, warehouseSelect, vendorInput, repInput,
            orderRefInput, vendorRefInput, shippingRefInput, amountInput, statusSelect
        ];

        allInputs.forEach(input => {
            if (input) {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyFilter();
                    }
                });
            }
        });

        // Clear filter function
        const clearFilter = () => {
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
            amountInput.value = '';
            statusSelect.value = '';

            let domain = [['state', 'in', ['draft', 'sent', 'to approve']]];

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Request for Quotation',
                res_model: 'purchase.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                context: {
                    'tree_view_ref': 'custom_purchase_rfq_list.purchase_order_tree_inherit_custom'
                },
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        // Clear button click
        clearBtn.addEventListener('click', clearFilter);

        // ESC key to clear filter
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearFilter();
            }
        });
    },
});