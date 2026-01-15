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
        this.orm = useService("orm");
        this._filterElement = null;
        this._filterData = {
            warehouses: [],
            customers: [],
            salespersons: []
        };

        onMounted(() => {
            if (this.shouldShowFilter()) {
                setTimeout(() => this.loadFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupFilter();
        });
    },

    shouldShowFilter() {
        if (this.props.resModel !== 'sale.order') {
            return false;
        }

        const action = this.env.config;

        if (action.xmlId === 'sale.action_orders') {
            return true;
        }

        if (action.displayName || action.name) {
            const actionName = (action.displayName || action.name).toLowerCase();
            if (actionName.includes('order') && !actionName.includes('quotation')) {
                return true;
            }
        }

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

    async loadFilterData() {
        try {
            // Load warehouses
            const warehouses = await this.orm.searchRead(
                'stock.warehouse',
                [],
                ['id', 'name'],
                { limit: 100 }
            );

            // Load customers (partners that are customers)
            const customers = await this.orm.searchRead(
                'res.partner',
                [['customer_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load salespersons (users)
            const salespersons = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            this._filterData = {
                warehouses: warehouses,
                customers: customers,
                salespersons: salespersons
            };

            this.injectDateFilter();
        } catch (error) {
            console.error('Error loading filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    injectDateFilter() {
        this.cleanupFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectDateFilter(), 100);
            return;
        }

        if (document.querySelector('.sale_date_filter_wrapper_main')) {
            return;
        }

        const timestamp = Date.now();
        const fromId = `date_from_${timestamp}`;
        const toId = `date_to_${timestamp}`;
        const warehouseId = `warehouse_${timestamp}`;
        const customerId = `customer_${timestamp}`;
        const salespersonId = `salesperson_${timestamp}`;
        const applyId = `apply_filter_${timestamp}`;
        const clearId = `clear_filter_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Build options for select dropdowns with data attributes for searching
        const warehouseOptions = this._filterData.warehouses
            .map(w => `<option value="${w.id}" data-name="${w.name.toLowerCase()}">${w.name}</option>`)
            .join('');

        const customerOptions = this._filterData.customers
            .map(c => `<option value="${c.id}" data-name="${c.name.toLowerCase()}">${c.name}</option>`)
            .join('');

        const salespersonOptions = this._filterData.salespersons
            .map(s => `<option value="${s.id}" data-name="${s.name.toLowerCase()}">${s.name}</option>`)
            .join('');

        const filterDiv = document.createElement('div');
        filterDiv.className = 'sale_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="sale_date_filter_container">
                <div class="date_filter_wrapper">
                    <!-- Date Range Filter -->
                    <div class="filter_group date_group">
                        <label class="filter_label">Order Date:</label>
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" />
                        </div>
                    </div>

                    <!-- Warehouse Filter with Search -->
                    <div class="filter_group select_group">
                        <label class="filter_label">Warehouse:</label>
                        <div class="select_search_wrapper">
                            <input type="text" class="form-control search_input" placeholder="Search..." id="${warehouseId}_search" />
                            <select class="form-select filter_select" id="${warehouseId}" size="1">
                                <option value="">All</option>
                                ${warehouseOptions}
                            </select>
                        </div>
                    </div>

                    <!-- Customer Filter with Search -->
                    <div class="filter_group select_group">
                        <label class="filter_label">Customer:</label>
                        <div class="select_search_wrapper">
                            <input type="text" class="form-control search_input" placeholder="Search..." id="${customerId}_search" />
                            <select class="form-select filter_select" id="${customerId}" size="1">
                                <option value="">All</option>
                                ${customerOptions}
                            </select>
                        </div>
                    </div>

                    <!-- Salesperson Filter with Search -->
                    <div class="filter_group select_group">
                        <label class="filter_label">Salesperson:</label>
                        <div class="select_search_wrapper">
                            <input type="text" class="form-control search_input" placeholder="Search..." id="${salespersonId}_search" />
                            <select class="form-select filter_select" id="${salespersonId}" size="1">
                                <option value="">All</option>
                                ${salespersonOptions}
                            </select>
                        </div>
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
        this._filterElement = filterDiv;

        this.attachFilterEvents(fromId, toId, warehouseId, customerId, salespersonId, applyId, clearId);
        this.setupSearchFilters(warehouseId, customerId, salespersonId);
    },

    setupSearchFilters(warehouseId, customerId, salespersonId) {
        // Setup search for warehouse
        this.setupSelectSearch(warehouseId);
        // Setup search for customer
        this.setupSelectSearch(customerId);
        // Setup search for salesperson
        this.setupSelectSearch(salespersonId);
    },

    setupSelectSearch(selectId) {
        const searchInput = document.getElementById(`${selectId}_search`);
        const selectElement = document.getElementById(selectId);

        if (!searchInput || !selectElement) return;

        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const options = selectElement.options;

            for (let i = 0; i < options.length; i++) {
                const option = options[i];
                if (i === 0) continue; // Skip "All" option

                const optionText = option.textContent.toLowerCase();
                if (optionText.includes(searchTerm)) {
                    option.style.display = '';
                } else {
                    option.style.display = 'none';
                }
            }

            // Auto-select if only one visible option (excluding "All")
            const visibleOptions = Array.from(options).filter((opt, idx) =>
                idx > 0 && opt.style.display !== 'none'
            );

            if (visibleOptions.length === 1) {
                selectElement.value = visibleOptions[0].value;
            }
        });

        // Clear search when select changes
        selectElement.addEventListener('change', () => {
            searchInput.value = '';
            const options = selectElement.options;
            for (let i = 0; i < options.length; i++) {
                options[i].style.display = '';
            }
        });
    },

    attachFilterEvents(fromId, toId, warehouseId, customerId, salespersonId, applyId, clearId) {
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const warehouseSelect = document.getElementById(warehouseId);
        const customerSelect = document.getElementById(customerId);
        const salespersonSelect = document.getElementById(salespersonId);
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

            // Build domain with all filters
            const domain = [
                ['date_order', '>=', dateFrom + ' 00:00:00'],
                ['date_order', '<=', dateTo + ' 23:59:59'],
                ['state', 'in', ['sale', 'done']]
            ];

            // Add warehouse filter
            if (warehouseSelect.value) {
                domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
            }

            // Add customer filter
            if (customerSelect.value) {
                domain.push(['partner_id', '=', parseInt(customerSelect.value)]);
            }

            // Add salesperson filter
            if (salespersonSelect.value) {
                domain.push(['user_id', '=', parseInt(salespersonSelect.value)]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Sale Orders',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
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
            customerSelect.value = '';
            salespersonSelect.value = '';

            // Clear search inputs
            document.getElementById(`${warehouseId}_search`).value = '';
            document.getElementById(`${customerId}_search`).value = '';
            document.getElementById(`${salespersonId}_search`).value = '';

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Sale Orders',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [['state', 'in', ['sale', 'done']]],
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        });
    },
});