/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for Delivery In/Out
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this._deliveryFilterElement = null;
        this._deliveryFilterData = {
            locations: [],
            customers: [],
            vendors: [],
            responsibles: []
        };

        onMounted(() => {
            if (this.shouldShowDeliveryFilter()) {
                setTimeout(() => this.loadDeliveryFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupDeliveryFilter();
        });
    },

    shouldShowDeliveryFilter() {
        const resModel = this.props.resModel;

        // Check if it's stock.picking (Delivery/Receipt)
        if (resModel === 'stock.picking') {
            const action = this.env.config;

            // Delivery Orders action
            if (action.xmlId === 'stock.action_picking_tree_all' ||
                action.xmlId === 'stock.action_picking_tree_ready' ||
                action.xmlId === 'stock.stock_picking_action_picking_type') {
                return true;
            }

            // Check action name
            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('delivery') ||
                    actionName.includes('receipt') ||
                    actionName.includes('transfer') ||
                    actionName.includes('picking')) {
                    return true;
                }
            }

            // Check domain for picking type
            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('picking_type_code')) {
                    return true;
                }
            }

            return true; // Show for all stock.picking views
        }

        return false;
    },

    cleanupDeliveryFilter() {
        if (this._deliveryFilterElement && this._deliveryFilterElement.parentNode) {
            this._deliveryFilterElement.remove();
            this._deliveryFilterElement = null;
        }
    },

    async loadDeliveryFilterData() {
        try {
            // Load locations
            const locations = await this.orm.searchRead(
                'stock.location',
                [['usage', '=', 'internal']],
                ['id', 'complete_name'],
                { limit: 200, order: 'complete_name' }
            );

            // Load customers (partners)
            const customers = await this.orm.searchRead(
                'res.partner',
                [['customer_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load vendors (suppliers)
            const vendors = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load responsible users
            const responsibles = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            this._deliveryFilterData = {
                locations: locations,
                customers: customers,
                vendors: vendors,
                responsibles: responsibles
            };

            this.injectDeliveryDateFilter();
        } catch (error) {
            console.error('Error loading delivery filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    getDeliveryViewType() {
        const action = this.env.config;

        // Check if it's incoming or outgoing
        if (this.props.domain) {
            const domainStr = JSON.stringify(this.props.domain);
            if (domainStr.includes('incoming')) {
                return 'incoming';
            }
            if (domainStr.includes('outgoing')) {
                return 'outgoing';
            }
        }

        // Check picking_type_code in domain
        if (this.props.domain) {
            for (let condition of this.props.domain) {
                if (Array.isArray(condition) && condition[0] === 'picking_type_code') {
                    if (condition[2] === 'incoming') {
                        return 'incoming';
                    }
                    if (condition[2] === 'outgoing') {
                        return 'outgoing';
                    }
                }
            }
        }

        // Default to all deliveries
        return 'all';
    },

    injectDeliveryDateFilter() {
        this.cleanupDeliveryFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectDeliveryDateFilter(), 100);
            return;
        }

        if (document.querySelector('.delivery_filter_wrapper_main')) {
            return;
        }

        const viewType = this.getDeliveryViewType();
        const timestamp = Date.now();

        // Determine if we should show Customer or Vendor
        const isIncoming = viewType === 'incoming';
        const partnerLabel = isIncoming ? 'Vendor' : 'Customer';
        const partnerPlaceholder = isIncoming ? 'Vendor' : 'Customer';
        const partnerData = isIncoming ? this._deliveryFilterData.vendors : this._deliveryFilterData.customers;

        // Field IDs
        const fromId = `delivery_date_from_${timestamp}`;
        const toId = `delivery_date_to_${timestamp}`;
        const numberId = `delivery_number_${timestamp}`;
        const partnerId = `delivery_partner_${timestamp}`;
        const locationId = `delivery_location_${timestamp}`;
        const sourceDocId = `delivery_source_doc_${timestamp}`;
        const responsibleId = `delivery_responsible_${timestamp}`;
        const statusId = `delivery_status_${timestamp}`;
        const applyId = `delivery_apply_${timestamp}`;
        const clearId = `delivery_clear_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Build location options
        const locationOptions = this._deliveryFilterData.locations
            .map(l => `<option value="${l.id}">${l.complete_name}</option>`)
            .join('');

        const filterHTML = `
            <div class="delivery_filter_container">
                <div class="date_filter_wrapper">
                    <!-- Date Range Filter -->
                    <div class="filter_group date_group">
                        <label class="filter_label">Scheduled Date:</label>
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
                        </div>
                    </div>

                    <!-- Number/Reference Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Number:</label>
                        <input type="text" class="form-control filter_input" id="${numberId}" placeholder="Number..." />
                    </div>

                    <!-- Partner Filter (Customer/Vendor based on view type) -->
                    <div class="filter_group autocomplete_group">
                        <label class="filter_label">${partnerLabel}:</label>
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input"
                                id="${partnerId}_input"
                                placeholder="${partnerPlaceholder}"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${partnerId}_value" />
                            <div class="autocomplete_dropdown" id="${partnerId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Source Location Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Source Location:</label>
                        <select class="form-select filter_select" id="${locationId}">
                            <option value="">Source Location</option>
                            ${locationOptions}
                        </select>
                    </div>

                    <!-- Source Document Filter -->
                    <div class="filter_group">
                        <label class="filter_label">Source Doc:</label>
                        <input type="text" class="form-control filter_input" id="${sourceDocId}" placeholder="Source Doc..." />
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
                            <option value="">Status</option>
                            <option value="draft">Draft</option>
                            <option value="waiting">Waiting</option>
                            <option value="confirmed">Confirmed</option>
                            <option value="assigned">Ready</option>
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

        const filterDiv = document.createElement('div');
        filterDiv.className = 'delivery_filter_wrapper_main';
        filterDiv.innerHTML = filterHTML;

        listTable.parentElement.insertBefore(filterDiv, listTable);
        this._deliveryFilterElement = filterDiv;

        // Setup autocomplete with appropriate data (vendors for incoming, customers for outgoing)
        this.setupDeliveryAutocomplete(partnerId, partnerData);
        this.setupDeliveryAutocomplete(responsibleId, this._deliveryFilterData.responsibles);

        this.attachDeliveryFilterEvents(
            fromId, toId, numberId, partnerId, locationId,
            sourceDocId, responsibleId, statusId,
            applyId, clearId, viewType
        );
    },

    setupDeliveryAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        input.addEventListener('focus', () => {
            this.filterDeliveryAutocomplete(fieldId, dataList, '');
            dropdown.classList.add('show');
        });

        input.addEventListener('input', (e) => {
            const searchTerm = e.target.value;
            hiddenValue.value = '';
            this.filterDeliveryAutocomplete(fieldId, dataList, searchTerm);
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

    filterDeliveryAutocomplete(fieldId, dataList, searchTerm) {
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

    attachDeliveryFilterEvents(
        fromId, toId, numberId, partnerId, locationId,
        sourceDocId, responsibleId, statusId,
        applyId, clearId, viewType
    ) {
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const numberInput = document.getElementById(numberId);
        const partnerValue = document.getElementById(`${partnerId}_value`);
        const partnerInput = document.getElementById(`${partnerId}_input`);
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
            try {
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

                // Number/Reference filter
                if (numberInput.value.trim()) {
                    domain.push(['name', 'ilike', numberInput.value.trim()]);
                }

                // Partner filter (Customer or Vendor)
                if (partnerValue.value) {
                    domain.push(['partner_id', '=', parseInt(partnerValue.value)]);
                }

                // Source Location filter
                if (locationSelect.value) {
                    domain.push(['location_id', '=', parseInt(locationSelect.value)]);
                }

                // Source Document filter
                if (sourceDocInput.value.trim()) {
                    domain.push(['origin', 'ilike', sourceDocInput.value.trim()]);
                }

                // Responsible filter
                if (responsibleValue.value) {
                    domain.push(['user_id', '=', parseInt(responsibleValue.value)]);
                }

                // Status filter
                if (statusSelect.value) {
                    domain.push(['state', '=', statusSelect.value]);
                }

                // Check if model and controller still exist before reloading
                if (this.model && this.model.load) {
                    this.model.load({ domain: domain }).catch((error) => {
                        console.warn('Model load warning:', error);
                    });
                    this.notification.add("Filters applied successfully", { type: "success" });
                }
            } catch (error) {
                console.error('Filter error:', error);
                this.notification.add("Error applying filters: " + error.message, { type: "danger" });
            }
        };

        // Click on Apply button
        applyBtn.addEventListener('click', applyFilter);

        // Press Enter on any input field to apply filter
        const allInputs = [
            dateFromInput, dateToInput, numberInput, partnerInput,
            locationSelect, sourceDocInput, responsibleInput, statusSelect
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
            try {
                const today = new Date();
                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                dateFromInput.value = firstDay.toISOString().split('T')[0];
                dateToInput.value = today.toISOString().split('T')[0];
                numberInput.value = '';
                partnerInput.value = '';
                partnerValue.value = '';
                locationSelect.value = '';
                sourceDocInput.value = '';
                responsibleInput.value = '';
                responsibleValue.value = '';
                statusSelect.value = '';

                let domain = [];

                // Check if model and controller still exist before reloading
                if (this.model && this.model.load) {
                    this.model.load({ domain: domain }).catch((error) => {
                        console.warn('Model load warning during clear:', error);
                    });
                    this.notification.add("Filters cleared successfully", { type: "info" });
                }
            } catch (error) {
                console.error('Clear filter error:', error);
                this.notification.add("Error clearing filters: " + error.message, { type: "danger" });
            }
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











///** @odoo-module **/
//
//import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//
//// Patch ListController to inject date filter for Delivery In/Out
//patch(ListController.prototype, {
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this.actionService = useService("action");
//        this.orm = useService("orm");
//        this._deliveryFilterElement = null;
//        this._deliveryFilterData = {
//            locations: [],
//            customers: [],
//            responsibles: []
//        };
//
//        onMounted(() => {
//            if (this.shouldShowDeliveryFilter()) {
//                setTimeout(() => this.loadDeliveryFilterData(), 150);
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupDeliveryFilter();
//        });
//    },
//
//    shouldShowDeliveryFilter() {
//        const resModel = this.props.resModel;
//
//        // Check if it's stock.picking (Delivery/Receipt)
//        if (resModel === 'stock.picking') {
//            const action = this.env.config;
//
//            // Delivery Orders action
//            if (action.xmlId === 'stock.action_picking_tree_all' ||
//                action.xmlId === 'stock.action_picking_tree_ready' ||
//                action.xmlId === 'stock.stock_picking_action_picking_type') {
//                return true;
//            }
//
//            // Check action name
//            if (action.displayName || action.name) {
//                const actionName = (action.displayName || action.name).toLowerCase();
//                if (actionName.includes('delivery') ||
//                    actionName.includes('receipt') ||
//                    actionName.includes('transfer') ||
//                    actionName.includes('picking')) {
//                    return true;
//                }
//            }
//
//            // Check domain for picking type
//            if (this.props.domain) {
//                const domainStr = JSON.stringify(this.props.domain);
//                if (domainStr.includes('picking_type_code')) {
//                    return true;
//                }
//            }
//
//            return true; // Show for all stock.picking views
//        }
//
//        return false;
//    },
//
//    cleanupDeliveryFilter() {
//        if (this._deliveryFilterElement && this._deliveryFilterElement.parentNode) {
//            this._deliveryFilterElement.remove();
//            this._deliveryFilterElement = null;
//        }
//    },
//
//    async loadDeliveryFilterData() {
//        try {
//            // Load locations
//            const locations = await this.orm.searchRead(
//                'stock.location',
//                [['usage', '=', 'internal']],
//                ['id', 'complete_name'],
//                { limit: 200, order: 'complete_name' }
//            );
//
//            // Load customers (partners)
//            const customers = await this.orm.searchRead(
//                'res.partner',
//                [['customer_rank', '>', 0]],
//                ['id', 'name'],
//                { limit: 500, order: 'name' }
//            );
//
//            // Load responsible users
//            const responsibles = await this.orm.searchRead(
//                'res.users',
//                [],
//                ['id', 'name'],
//                { limit: 100, order: 'name' }
//            );
//
//            this._deliveryFilterData = {
//                locations: locations,
//                customers: customers,
//                responsibles: responsibles
//            };
//
//            this.injectDeliveryDateFilter();
//        } catch (error) {
//            console.error('Error loading delivery filter data:', error);
//            this.notification.add("Error loading filter options", { type: "danger" });
//        }
//    },
//
//    getDeliveryViewType() {
//        const action = this.env.config;
//
//        // Check if it's incoming or outgoing
//        if (this.props.domain) {
//            const domainStr = JSON.stringify(this.props.domain);
//            if (domainStr.includes('incoming')) {
//                return 'incoming';
//            }
//            if (domainStr.includes('outgoing')) {
//                return 'outgoing';
//            }
//        }
//
//        // Default to all deliveries
//        return 'all';
//    },
//
//    injectDeliveryDateFilter() {
//        this.cleanupDeliveryFilter();
//
//        const listTable = document.querySelector('.o_list_table');
//
//        if (!listTable) {
//            setTimeout(() => this.injectDeliveryDateFilter(), 100);
//            return;
//        }
//
//        if (document.querySelector('.delivery_filter_wrapper_main')) {
//            return;
//        }
//
//        const viewType = this.getDeliveryViewType();
//        const timestamp = Date.now();
//
//        // Field IDs
//        const fromId = `delivery_date_from_${timestamp}`;
//        const toId = `delivery_date_to_${timestamp}`;
//        const numberId = `delivery_number_${timestamp}`;
//        const customerId = `delivery_customer_${timestamp}`;
//        const locationId = `delivery_location_${timestamp}`;
//        const sourceDocId = `delivery_source_doc_${timestamp}`;
//        const responsibleId = `delivery_responsible_${timestamp}`;
//        const statusId = `delivery_status_${timestamp}`;
//        const applyId = `delivery_apply_${timestamp}`;
//        const clearId = `delivery_clear_${timestamp}`;
//
//        const today = new Date();
//        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//        const dateFrom = firstDay.toISOString().split('T')[0];
//        const dateTo = today.toISOString().split('T')[0];
//
//        // Build location options
//        const locationOptions = this._deliveryFilterData.locations
//            .map(l => `<option value="${l.id}">${l.complete_name}</option>`)
//            .join('');
//
//        const filterHTML = `
//            <div class="delivery_filter_container">
//                <div class="date_filter_wrapper">
//                    <!-- Date Range Filter -->
//                    <div class="filter_group date_group">
//                        <label class="filter_label">Scheduled Date:</label>
//                        <div class="date_input_group">
//                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
//                            <span class="date_separator">→</span>
//                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
//                        </div>
//                    </div>
//
//                    <!-- Number/Reference Filter -->
//                    <div class="filter_group">
//                        <label class="filter_label">Number:</label>
//                        <input type="text" class="form-control filter_input" id="${numberId}" placeholder="Number..." />
//                    </div>
//
//                    <!-- Customer Filter (Searchable) -->
//                    <div class="filter_group autocomplete_group">
//                        <label class="filter_label">Customer:</label>
//                        <div class="autocomplete_wrapper">
//                            <input
//                                type="text"
//                                class="form-control autocomplete_input"
//                                id="${customerId}_input"
//                                placeholder="Customer"
//                                autocomplete="off"
//                            />
//                            <input type="hidden" id="${customerId}_value" />
//                            <div class="autocomplete_dropdown" id="${customerId}_dropdown"></div>
//                        </div>
//                    </div>
//
//                    <!-- Source Location Filter -->
//                    <div class="filter_group">
//                        <label class="filter_label">Source Location:</label>
//                        <select class="form-select filter_select" id="${locationId}">
//                            <option value="">Source Location</option>
//                            ${locationOptions}
//                        </select>
//                    </div>
//
//                    <!-- Source Document Filter -->
//                    <div class="filter_group">
//                        <label class="filter_label">Source Doc:</label>
//                        <input type="text" class="form-control filter_input" id="${sourceDocId}" placeholder="Source Doc..." />
//                    </div>
//
//                    <!-- Responsible Filter (Searchable) -->
//                    <div class="filter_group autocomplete_group">
//                        <label class="filter_label">Responsible:</label>
//                        <div class="autocomplete_wrapper">
//                            <input
//                                type="text"
//                                class="form-control autocomplete_input"
//                                id="${responsibleId}_input"
//                                placeholder="Responsible"
//                                autocomplete="off"
//                            />
//                            <input type="hidden" id="${responsibleId}_value" />
//                            <div class="autocomplete_dropdown" id="${responsibleId}_dropdown"></div>
//                        </div>
//                    </div>
//
//                    <!-- Status Filter -->
//                    <div class="filter_group">
//                        <label class="filter_label">Status:</label>
//                        <select class="form-select filter_select" id="${statusId}">
//                            <option value="">Status</option>
//                            <option value="draft">Draft</option>
//                            <option value="waiting">Waiting</option>
//                            <option value="confirmed">Confirmed</option>
//                            <option value="assigned">Ready</option>
//                            <option value="done">Done</option>
//                            <option value="cancel">Cancelled</option>
//                        </select>
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
//        const filterDiv = document.createElement('div');
//        filterDiv.className = 'delivery_filter_wrapper_main';
//        filterDiv.innerHTML = filterHTML;
//
//        listTable.parentElement.insertBefore(filterDiv, listTable);
//        this._deliveryFilterElement = filterDiv;
//
//        // Setup autocomplete
//        this.setupDeliveryAutocomplete(customerId, this._deliveryFilterData.customers);
//        this.setupDeliveryAutocomplete(responsibleId, this._deliveryFilterData.responsibles);
//
//        this.attachDeliveryFilterEvents(
//            fromId, toId, numberId, customerId, locationId,
//            sourceDocId, responsibleId, statusId,
//            applyId, clearId, viewType
//        );
//    },
//
//    setupDeliveryAutocomplete(fieldId, dataList) {
//        const input = document.getElementById(`${fieldId}_input`);
//        const hiddenValue = document.getElementById(`${fieldId}_value`);
//        const dropdown = document.getElementById(`${fieldId}_dropdown`);
//
//        if (!input || !dropdown || !hiddenValue) return;
//
//        input.addEventListener('focus', () => {
//            this.filterDeliveryAutocomplete(fieldId, dataList, '');
//            dropdown.classList.add('show');
//        });
//
//        input.addEventListener('input', (e) => {
//            const searchTerm = e.target.value;
//            hiddenValue.value = '';
//            this.filterDeliveryAutocomplete(fieldId, dataList, searchTerm);
//            dropdown.classList.add('show');
//        });
//
//        input.addEventListener('keypress', (e) => {
//            if (e.key === 'Enter') {
//                dropdown.classList.remove('show');
//                const applyBtn = document.querySelector('.apply_filter_btn');
//                if (applyBtn) {
//                    applyBtn.click();
//                }
//            }
//        });
//
//        document.addEventListener('click', (e) => {
//            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
//                dropdown.classList.remove('show');
//            }
//        });
//    },
//
//    filterDeliveryAutocomplete(fieldId, dataList, searchTerm) {
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
//    attachDeliveryFilterEvents(
//        fromId, toId, numberId, customerId, locationId,
//        sourceDocId, responsibleId, statusId,
//        applyId, clearId, viewType
//    ) {
//        const dateFromInput = document.getElementById(fromId);
//        const dateToInput = document.getElementById(toId);
//        const numberInput = document.getElementById(numberId);
//        const customerValue = document.getElementById(`${customerId}_value`);
//        const customerInput = document.getElementById(`${customerId}_input`);
//        const locationSelect = document.getElementById(locationId);
//        const sourceDocInput = document.getElementById(sourceDocId);
//        const responsibleValue = document.getElementById(`${responsibleId}_value`);
//        const responsibleInput = document.getElementById(`${responsibleId}_input`);
//        const statusSelect = document.getElementById(statusId);
//        const applyBtn = document.getElementById(applyId);
//        const clearBtn = document.getElementById(clearId);
//
//        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) return;
//
//        // Apply filter function
//        const applyFilter = () => {
//            try {
//                const dateFrom = dateFromInput.value;
//                const dateTo = dateToInput.value;
//
//                if (!dateFrom || !dateTo) {
//                    this.notification.add("Please select both dates", { type: "warning" });
//                    return;
//                }
//
//                if (dateFrom > dateTo) {
//                    this.notification.add("Start date must be before end date", { type: "warning" });
//                    return;
//                }
//
//                let domain = [
//                    ['scheduled_date', '>=', dateFrom + ' 00:00:00'],
//                    ['scheduled_date', '<=', dateTo + ' 23:59:59']
//                ];
//
//                // Number/Reference filter
//                if (numberInput.value.trim()) {
//                    domain.push(['name', 'ilike', numberInput.value.trim()]);
//                }
//
//                // Customer filter
//                if (customerValue.value) {
//                    domain.push(['partner_id', '=', parseInt(customerValue.value)]);
//                }
//
//                // Source Location filter
//                if (locationSelect.value) {
//                    domain.push(['location_id', '=', parseInt(locationSelect.value)]);
//                }
//
//                // Source Document filter
//                if (sourceDocInput.value.trim()) {
//                    domain.push(['origin', 'ilike', sourceDocInput.value.trim()]);
//                }
//
//                // Responsible filter
//                if (responsibleValue.value) {
//                    domain.push(['user_id', '=', parseInt(responsibleValue.value)]);
//                }
//
//                // Status filter
//                if (statusSelect.value) {
//                    domain.push(['state', '=', statusSelect.value]);
//                }
//
//                // Check if model and controller still exist before reloading
//                if (this.model && this.model.load) {
//                    this.model.load({ domain: domain }).catch((error) => {
//                        console.warn('Model load warning:', error);
//                    });
//                    this.notification.add("Filters applied successfully", { type: "success" });
//                }
//            } catch (error) {
//                console.error('Filter error:', error);
//                this.notification.add("Error applying filters: " + error.message, { type: "danger" });
//            }
//        };
//
//        // Click on Apply button
//        applyBtn.addEventListener('click', applyFilter);
//
//        // Press Enter on any input field to apply filter
//        const allInputs = [
//            dateFromInput, dateToInput, numberInput, customerInput,
//            locationSelect, sourceDocInput, responsibleInput, statusSelect
//        ];
//
//        allInputs.forEach(input => {
//            if (input) {
//                input.addEventListener('keypress', (e) => {
//                    if (e.key === 'Enter') {
//                        e.preventDefault();
//                        applyFilter();
//                    }
//                });
//            }
//        });
//
//        // Clear filter function
//        const clearFilter = () => {
//            try {
//                const today = new Date();
//                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//                dateFromInput.value = firstDay.toISOString().split('T')[0];
//                dateToInput.value = today.toISOString().split('T')[0];
//                numberInput.value = '';
//                customerInput.value = '';
//                customerValue.value = '';
//                locationSelect.value = '';
//                sourceDocInput.value = '';
//                responsibleInput.value = '';
//                responsibleValue.value = '';
//                statusSelect.value = '';
//
//                let domain = [];
//
//                // Check if model and controller still exist before reloading
//                if (this.model && this.model.load) {
//                    this.model.load({ domain: domain }).catch((error) => {
//                        console.warn('Model load warning during clear:', error);
//                    });
//                    this.notification.add("Filters cleared successfully", { type: "info" });
//                }
//            } catch (error) {
//                console.error('Clear filter error:', error);
//                this.notification.add("Error clearing filters: " + error.message, { type: "danger" });
//            }
//        };
//
//        // Clear button click
//        clearBtn.addEventListener('click', clearFilter);
//
//        // ESC key to clear filter
//        document.addEventListener('keydown', (e) => {
//            if (e.key === 'Escape') {
//                clearFilter();
//            }
//        });
//    },
//});