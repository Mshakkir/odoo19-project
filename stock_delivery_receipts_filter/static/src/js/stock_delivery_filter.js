/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for Delivery Notes and Receipts
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this._stockFilterElement = null;
        this._stockFilterData = {
            locations: [],
            customers: [],
            suppliers: [],
            users: []
        };

        onMounted(() => {
            if (this.shouldShowStockFilter()) {
                setTimeout(() => this.loadStockFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupStockFilter();
        });
    },

    shouldShowStockFilter() {
        const resModel = this.props.resModel;

        if (resModel !== 'stock.picking') {
            return false;
        }

        const action = this.env.config;
        const actionName = (action.displayName || action.name || '').toLowerCase();

        // Check for Delivery Notes
        if (actionName.includes('delivery') ||
            action.xmlId === 'stock.action_picking_tree_out' ||
            action.xmlId === 'stock.action_picking_tree_all') {
            return true;
        }

        // Check for Receipts
        if (actionName.includes('receipt') ||
            actionName.includes('incoming') ||
            action.xmlId === 'stock.action_picking_tree_in') {
            return true;
        }

        return false;
    },

    cleanupStockFilter() {
        if (this._stockFilterElement && this._stockFilterElement.parentNode) {
            this._stockFilterElement.remove();
            this._stockFilterElement = null;
        }
    },

    async loadStockFilterData() {
        try {
            // Load source locations
            const locations = await this.orm.searchRead(
                'stock.location',
                [['usage', 'in', ['internal', 'transit']]],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            // Load customers (partners that are customers)
            const customers = await this.orm.searchRead(
                'res.partner',
                [['customer_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load suppliers (partners that are suppliers)
            const suppliers = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load users (for responsible filter)
            const users = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            this._stockFilterData = {
                locations: locations,
                customers: customers,
                suppliers: suppliers,
                users: users
            };

            this.injectStockFilter();
        } catch (error) {
            console.error('Error loading stock filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    injectStockFilter() {
        this.cleanupStockFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectStockFilter(), 100);
            return;
        }

        if (document.querySelector('.stock_delivery_filter_wrapper_main')) {
            return;
        }

        const timestamp = Date.now();
        const dateId = `stock_date_${timestamp}`;
        const numberId = `stock_number_${timestamp}`;
        const customerId = `stock_customer_${timestamp}`;
        const locationId = `stock_location_${timestamp}`;
        const sourceDocId = `stock_source_doc_${timestamp}`;
        const responsibleId = `stock_responsible_${timestamp}`;
        const statusId = `stock_status_${timestamp}`;
        const applyId = `stock_apply_${timestamp}`;
        const clearId = `stock_clear_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Determine if this is Delivery Notes or Receipts
        const action = this.env.config;
        const actionName = (action.displayName || action.name || '').toLowerCase();
        const isDelivery = actionName.includes('delivery') || action.xmlId === 'stock.action_picking_tree_out';
        const isReceipt = actionName.includes('receipt') || actionName.includes('incoming') || action.xmlId === 'stock.action_picking_tree_in';

        // Build options for location dropdown
        const locationOptions = this._stockFilterData.locations
            .map(l => `<option value="${l.id}">${l.name}</option>`)
            .join('');

        const filterDiv = document.createElement('div');
        filterDiv.className = 'stock_delivery_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="stock_delivery_filter_container">
                <div class="date_filter_wrapper">
                    <!-- Scheduled Date Filter -->
                    <div class="filter_group date_group">
                        <label class="filter_label">Scheduled Date:</label>
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input" id="${dateId}_from" value="${dateFrom}" placeholder="From" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input" id="${dateId}_to" value="${dateTo}" placeholder="To" />
                        </div>
                    </div>

                    <!-- Reference/Number Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Number:</label>
                        <input type="text" class="form-control filter_input" id="${numberId}" placeholder="Reference..." />
                    </div>

                    <!-- Customer/Partner Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">Customer:</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${customerId}_input"
                                placeholder="Customer"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${customerId}_value" />
                            <div class="autocomplete_dropdown" id="${customerId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Source Location Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Source Location:</label>
                        <select class="form-select filter_select" id="${locationId}">
                            <option value="">Location</option>
                            ${locationOptions}
                        </select>
                    </div>

                    <!-- Source Document Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Source Document:</label>
                        <input type="text" class="form-control filter_input" id="${sourceDocId}" placeholder="Origin..." />
                    </div>

                    <!-- Responsible Filter (Searchable) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">Responsible:</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${responsibleId}_input"
                                placeholder="Responsible"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${responsibleId}_value" />
                            <div class="autocomplete_dropdown" id="${responsibleId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Status Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Status:</label>
                        <select class="form-select filter_select" id="${statusId}">
                            <option value="">All Status</option>
                            <option value="draft">Draft</option>
                            <option value="waiting">Waiting</option>
                            <option value="confirmed">Confirmed</option>
                            <option value="assigned">Assigned</option>
                            <option value="done">Done</option>
                            <option value="cancel">Cancelled</option>
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
        this._stockFilterElement = filterDiv;

        // Setup autocomplete
        this.setupStockAutocomplete(customerId, this._stockFilterData.customers);
        this.setupStockAutocomplete(responsibleId, this._stockFilterData.users);

        this.attachStockFilterEvents(
            dateId, numberId, customerId, locationId, sourceDocId, responsibleId, statusId,
            applyId, clearId, isDelivery, isReceipt
        );
    },

    setupStockAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        input.addEventListener('focus', () => {
            this.filterStockAutocomplete(fieldId, dataList, '');
            dropdown.classList.add('show');
        });

        input.addEventListener('input', (e) => {
            const searchTerm = e.target.value;
            hiddenValue.value = '';
            this.filterStockAutocomplete(fieldId, dataList, searchTerm);
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

    filterStockAutocomplete(fieldId, dataList, searchTerm) {
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

    attachStockFilterEvents(
        dateId, numberId, customerId, locationId, sourceDocId, responsibleId, statusId,
        applyId, clearId, isDelivery, isReceipt
    ) {
        const dateFromInput = document.getElementById(`${dateId}_from`);
        const dateToInput = document.getElementById(`${dateId}_to`);
        const numberInput = document.getElementById(numberId);
        const customerValue = document.getElementById(`${customerId}_value`);
        const customerInput = document.getElementById(`${customerId}_input`);
        const locationSelect = document.getElementById(locationId);
        const sourceDocInput = document.getElementById(sourceDocId);
        const responsibleValue = document.getElementById(`${responsibleId}_value`);
        const responsibleInput = document.getElementById(`${responsibleId}_input`);
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
                ['scheduled_date', '>=', dateFrom + ' 00:00:00'],
                ['scheduled_date', '<=', dateTo + ' 23:59:59']
            ];

            // Add reference/number filter
            if (numberInput.value.trim()) {
                domain.push(['name', 'ilike', numberInput.value.trim()]);
            }

            // Add customer filter
            if (customerValue.value) {
                domain.push(['partner_id', '=', parseInt(customerValue.value)]);
            }

            // Add source location filter
            if (locationSelect.value) {
                domain.push(['location_id', '=', parseInt(locationSelect.value)]);
            }

            // Add source document filter
            if (sourceDocInput.value.trim()) {
                domain.push(['origin', 'ilike', sourceDocInput.value.trim()]);
            }

            // Add responsible filter
            if (responsibleValue.value) {
                domain.push(['user_id', '=', parseInt(responsibleValue.value)]);
            }

            // Add status filter
            if (statusSelect.value) {
                domain.push(['state', '=', statusSelect.value]);
            }

            // Apply filter using Odoo's native filtering
            this.env.searchModel.setDomain(domain);

            this.notification.add("Filters applied", { type: "success" });
        };

        // Click on Apply button
        applyBtn.addEventListener('click', applyFilter);

        // Press Enter on any input field to apply filter
        const allInputs = [
            dateFromInput, dateToInput, numberInput, customerInput, locationSelect,
            sourceDocInput, responsibleInput, statusSelect
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
            numberInput.value = '';
            customerInput.value = '';
            customerValue.value = '';
            locationSelect.value = '';
            sourceDocInput.value = '';
            responsibleInput.value = '';
            responsibleValue.value = '';
            statusSelect.value = '';

            // Reset to default domain
            this.env.searchModel.setDomain([]);

            this.notification.add("Filters cleared", { type: "info" });
        };

        // Clear button click
        clearBtn.addEventListener('click', clearFilter);

        // Backspace key anywhere to trigger clear filter
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace') {
                clearFilter();
            }
        });
    },
});