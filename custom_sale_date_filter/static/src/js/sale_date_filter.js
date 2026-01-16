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
        const resModel = this.props.resModel;

        // ONLY show filter for Sale Orders, NOT for invoices
        if (resModel === 'sale.order') {
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

            return true;
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
        const documentNumberId = `doc_number_${timestamp}`;
        const totalAmountId = `total_amount_${timestamp}`;
        const applyId = `apply_filter_${timestamp}`;
        const clearId = `clear_filter_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // This is ONLY for Sale Orders
        const documentNumberPlaceholder = 'Sale Order Number';
        const actionName = 'Sale Orders';

        // Build options for warehouse dropdown - Always show for Sale Orders
        const warehouseOptions = this._filterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        const warehouseFilter = `
            <div class="filter_group filter_group_small">
                <select class="form-select filter_select_small" id="${warehouseId}">
                    <option value="">Warehouse</option>
                    ${warehouseOptions}
                </select>
            </div>
        `;

        const customerRefId = `customer_ref_${timestamp}`;
        const poNumberId = `po_number_${timestamp}`;
        const shippingRefId = `shipping_ref_${timestamp}`;

        const filterDiv = document.createElement('div');
        filterDiv.className = 'sale_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="sale_date_filter_container">
                <div class="date_filter_wrapper">
                    <!-- 1. Date Range Filter (Small) -->
                    <div class="filter_group filter_group_small date_group_small">
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input_small" id="${fromId}" value="${dateFrom}" placeholder="From" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input_small" id="${toId}" value="${dateTo}" placeholder="To" />
                        </div>
                    </div>

                    <!-- 2. Document Number Filter (Small) -->
                    <div class="filter_group filter_group_small">
                        <input
                            type="text"
                            class="form-control filter_input_small"
                            id="${documentNumberId}"
                            placeholder="${documentNumberPlaceholder}"
                            autocomplete="off"
                        />
                    </div>

                    <!-- 3. Customer Filter (Small) -->
                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input_small"
                                id="${customerId}_input"
                                placeholder="Customer"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${customerId}_value" />
                            <div class="autocomplete_dropdown" id="${customerId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- 4. Warehouse Filter (Small) -->
                    ${warehouseFilter}

                    <!-- 5. Customer Reference Filter (Small) -->
                    <div class="filter_group filter_group_small">
                        <input
                            type="text"
                            class="form-control filter_input_small"
                            id="${customerRefId}"
                            placeholder="Customer Reference"
                            autocomplete="off"
                        />
                    </div>

                    <!-- 6. Salesperson Filter (Small) -->
                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input
                                type="text"
                                class="form-control autocomplete_input_small"
                                id="${salespersonId}_input"
                                placeholder="Salesperson"
                                autocomplete="off"
                            />
                            <input type="hidden" id="${salespersonId}_value" />
                            <div class="autocomplete_dropdown" id="${salespersonId}_dropdown"></div>
                        </div>
                    </div>

                    <!-- 7. Total Amount Filter (Small) -->
                    <div class="filter_group filter_group_small">
                        <input
                            type="number"
                            class="form-control filter_input_small"
                            id="${totalAmountId}"
                            placeholder="Total Amount"
                            step="0.01"
                            min="0"
                        />
                    </div>

                    <!-- 8. PO Number Filter (Small) -->
                    <div class="filter_group filter_group_small">
                        <input
                            type="text"
                            class="form-control filter_input_small"
                            id="${poNumberId}"
                            placeholder="PO Number"
                            autocomplete="off"
                        />
                    </div>

                    <!-- 9. Shipping Reference Filter (Small) -->
                    <div class="filter_group filter_group_small">
                        <input
                            type="text"
                            class="form-control filter_input_small"
                            id="${shippingRefId}"
                            placeholder="Shipping Ref"
                            autocomplete="off"
                        />
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

        // Setup autocomplete for customer and salesperson
        this.setupAutocomplete(customerId, this._filterData.customers);
        this.setupAutocomplete(salespersonId, this._filterData.salespersons);

        this.attachFilterEvents(fromId, toId, warehouseId, customerId, salespersonId, documentNumberId, totalAmountId, customerRefId, poNumberId, shippingRefId, applyId, clearId, actionName);
    },

    setupAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        // Show dropdown on focus
        input.addEventListener('focus', () => {
            this.filterAutocomplete(fieldId, dataList, '');
            dropdown.classList.add('show');
        });

        // Filter as user types
        input.addEventListener('input', (e) => {
            const searchTerm = e.target.value;
            hiddenValue.value = ''; // Clear hidden value when typing
            this.filterAutocomplete(fieldId, dataList, searchTerm);
            dropdown.classList.add('show');
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    },

    filterAutocomplete(fieldId, dataList, searchTerm) {
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

        // Add click handlers to dropdown items
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

    attachFilterEvents(fromId, toId, warehouseId, customerId, salespersonId, documentNumberId, totalAmountId, customerRefId, poNumberId, shippingRefId, applyId, clearId, actionName) {
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const warehouseSelect = document.getElementById(warehouseId);
        const customerValue = document.getElementById(`${customerId}_value`);
        const customerInput = document.getElementById(`${customerId}_input`);
        const salespersonValue = document.getElementById(`${salespersonId}_value`);
        const salespersonInput = document.getElementById(`${salespersonId}_input`);
        const documentNumberInput = document.getElementById(documentNumberId);
        const totalAmountInput = document.getElementById(totalAmountId);
        const customerRefInput = document.getElementById(customerRefId);
        const poNumberInput = document.getElementById(poNumberId);
        const shippingRefInput = document.getElementById(shippingRefId);
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

            // Build domain for Sale Orders ONLY
            let domain = [
                ['date_order', '>=', dateFrom + ' 00:00:00'],
                ['date_order', '<=', dateTo + ' 23:59:59'],
                ['state', 'in', ['sale', 'done']]
            ];

            // Add warehouse filter
            if (warehouseSelect && warehouseSelect.value) {
                domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
            }

            // Add customer filter
            if (customerValue.value) {
                domain.push(['partner_id', '=', parseInt(customerValue.value)]);
            }

            // Add salesperson filter
            if (salespersonValue.value) {
                domain.push(['user_id', '=', parseInt(salespersonValue.value)]);
            }

            // Add document number filter
            if (documentNumberInput.value.trim()) {
                domain.push(['name', 'ilike', documentNumberInput.value.trim()]);
            }

            // Add total amount filter
            if (totalAmountInput.value && parseFloat(totalAmountInput.value) > 0) {
                const amount = parseFloat(totalAmountInput.value);
                domain.push(['amount_total', '=', amount]);
            }

            // Add customer reference filter
            if (customerRefInput.value.trim()) {
                domain.push(['client_order_ref', 'ilike', customerRefInput.value.trim()]);
            }

            // Add PO number filter
            if (poNumberInput.value.trim()) {
                domain.push(['client_order_ref', 'ilike', poNumberInput.value.trim()]);
            }

            // Add shipping reference filter
            if (shippingRefInput.value.trim()) {
                domain.push(['name', 'ilike', shippingRefInput.value.trim()]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: actionName,
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
            if (warehouseSelect) warehouseSelect.value = '';
            customerInput.value = '';
            customerValue.value = '';
            salespersonInput.value = '';
            salespersonValue.value = '';
            documentNumberInput.value = '';
            totalAmountInput.value = '';
            customerRefInput.value = '';
            poNumberInput.value = '';
            shippingRefInput.value = '';

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: actionName,
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [['state', 'in', ['sale', 'done']]],
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        });
    },
});