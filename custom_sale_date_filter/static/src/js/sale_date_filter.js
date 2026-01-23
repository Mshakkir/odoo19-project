/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

let filterInstanceCount = 0;

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
        this._applyFiltersCallback = null;
        this._filterEventListeners = []; // Store listeners for cleanup
        this._instanceId = ++filterInstanceCount;

        onMounted(async () => {
            if (this.shouldShowFilter()) {
                try {
                    await this.loadFilterData();
                    this.injectDateFilter();
                } catch (error) {
                    console.error('Filter initialization error:', error);
                }
            }
        });

        onWillUnmount(() => {
            this.cleanupFilter();
        });
    },

    shouldShowFilter() {
        const resModel = this.props.resModel;

        if (resModel === 'sale.order') {
            return true;
        }

        if (resModel === 'account.move') {
            const action = this.env.config;
            if (action.xmlId === 'sale.action_invoices' ||
                action.xmlId === 'account.action_move_out_invoice_type') {
                return true;
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('invoice') &&
                    (actionName.includes('sale') || actionName.includes('customer'))) {
                    return true;
                }
            }
        }

        return false;
    },

    cleanupFilter() {
        // Remove event listeners
        this._filterEventListeners.forEach(({ element, event, handler }) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        this._filterEventListeners = [];

        // Remove filter DOM
        if (this._filterElement && this._filterElement.parentNode) {
            this._filterElement.remove();
            this._filterElement = null;
        }
    },

    addEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            this._filterEventListeners.push({ element, event, handler });
        }
    },

    async loadFilterData() {
        try {
            const [warehouses, customers, salespersons] = await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }),
                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' })
            ]);

            this._filterData = {
                warehouses: warehouses,
                customers: customers,
                salespersons: salespersons
            };
        } catch (error) {
            console.error('Error loading filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
            throw error;
        }
    },

    injectDateFilter() {
        const listTable = document.querySelector('.o_list_table');
        if (!listTable) {
            console.warn('List table not found');
            return;
        }

        if (document.querySelector('.sale_date_filter_wrapper_main')) {
            return;
        }

        const timestamp = this._instanceId;
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        const isSaleOrder = this.props.resModel === 'sale.order';
        const isInvoice = this.props.resModel === 'account.move';

        const filterDiv = document.createElement('div');
        filterDiv.className = 'sale_date_filter_wrapper_main';
        filterDiv.innerHTML = this.buildFilterHTML({
            timestamp,
            dateFrom,
            dateTo,
            isSaleOrder,
            isInvoice
        });

        listTable.parentElement.insertBefore(filterDiv, listTable);
        this._filterElement = filterDiv;

        this.attachFilterEvents(timestamp, isSaleOrder, isInvoice);
    },

    buildFilterHTML(options) {
        const { timestamp, dateFrom, dateTo, isSaleOrder, isInvoice } = options;

        const warehouseOptions = this._filterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        return `
            <div class="sale_date_filter_container">
                <div class="date_filter_wrapper">
                    <!-- Date Range -->
                    <div class="filter_group filter_group_small date_group_small">
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input_small filter-input"
                                id="date_from_${timestamp}" value="${dateFrom}" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input_small filter-input"
                                id="date_to_${timestamp}" value="${dateTo}" />
                        </div>
                    </div>

                    <!-- Document Number -->
                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small filter-input"
                            id="doc_number_${timestamp}"
                            placeholder="${isSaleOrder ? 'Sale Order/Quotation' : 'Invoice Number'}" />
                    </div>

                    <!-- Customer -->
                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input type="text" class="form-control autocomplete_input_small filter-input autocomplete-input"
                                id="customer_${timestamp}_input" placeholder="Customer" />
                            <input type="hidden" id="customer_${timestamp}_value" />
                            <div class="autocomplete_dropdown" id="customer_${timestamp}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Warehouse -->
                    <div class="filter_group filter_group_small">
                        <select class="form-select filter_select_small" id="warehouse_${timestamp}">
                            <option value="">Warehouse</option>
                            ${warehouseOptions}
                        </select>
                    </div>

                    <!-- Customer Reference -->
                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small filter-input"
                            id="customer_ref_${timestamp}" placeholder="Customer Ref" />
                    </div>

                    <!-- Salesperson -->
                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input type="text" class="form-control autocomplete_input_small filter-input autocomplete-input"
                                id="salesperson_${timestamp}_input" placeholder="Salesperson" />
                            <input type="hidden" id="salesperson_${timestamp}_value" />
                            <div class="autocomplete_dropdown" id="salesperson_${timestamp}_dropdown"></div>
                        </div>
                    </div>

                    <!-- Total Amount -->
                    <div class="filter_group filter_group_small">
                        <input type="number" class="form-control filter_input_small filter-input"
                            id="total_amount_${timestamp}" placeholder="Total Amount" step="0.01" min="0" />
                    </div>

                    <!-- AWB Number -->
                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small filter-input"
                            id="awb_number_${timestamp}" placeholder="AWB Number" />
                    </div>

                    <!-- Action Buttons -->
                    <div class="filter_actions">
                        <button class="btn btn-primary apply_filter_btn" id="apply_filter_${timestamp}">Apply</button>
                        <button class="btn btn-secondary clear_filter_btn" id="clear_filter_${timestamp}">Clear</button>
                    </div>
                </div>
            </div>
        `;
    },

    setupAutocomplete(fieldId, dataList) {
        const input = document.getElementById(`${fieldId}_input`);
        const hiddenValue = document.getElementById(`${fieldId}_value`);
        const dropdown = document.getElementById(`${fieldId}_dropdown`);

        if (!input || !dropdown || !hiddenValue) return;

        let selectedIndex = -1;

        const filterAutocomplete = (searchTerm) => {
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
                this.addEventListener(item, 'click', () => {
                    const id = item.getAttribute('data-id');
                    const name = item.getAttribute('data-name');
                    input.value = name;
                    hiddenValue.value = id;
                    dropdown.classList.remove('show');
                });
            });
        };

        this.addEventListener(input, 'focus', () => {
            filterAutocomplete('');
            dropdown.classList.add('show');
            selectedIndex = -1;
        });

        this.addEventListener(input, 'input', (e) => {
            hiddenValue.value = '';
            filterAutocomplete(e.target.value);
            dropdown.classList.add('show');
            selectedIndex = -1;
        });

        this.addEventListener(input, 'keydown', (e) => {
            const items = dropdown.querySelectorAll('.autocomplete_item:not(.no_results)');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.updateAutocompleteSelection(items, selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                this.updateAutocompleteSelection(items, selectedIndex);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedIndex >= 0 && items.length > 0) {
                    const selectedItem = items[selectedIndex];
                    const id = selectedItem.getAttribute('data-id');
                    const name = selectedItem.getAttribute('data-name');
                    input.value = name;
                    hiddenValue.value = id;
                    dropdown.classList.remove('show');
                    selectedIndex = -1;
                }
                if (this._applyFiltersCallback) {
                    this._applyFiltersCallback();
                }
            } else if (e.key === 'Escape') {
                dropdown.classList.remove('show');
                selectedIndex = -1;
            }
        });
    },

    updateAutocompleteSelection(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    },

    attachFilterEvents(timestamp, isSaleOrder, isInvoice) {
        const dateFromInput = document.getElementById(`date_from_${timestamp}`);
        const dateToInput = document.getElementById(`date_to_${timestamp}`);
        const warehouseSelect = document.getElementById(`warehouse_${timestamp}`);
        const customerValue = document.getElementById(`customer_${timestamp}_value`);
        const customerInput = document.getElementById(`customer_${timestamp}_input`);
        const salespersonValue = document.getElementById(`salesperson_${timestamp}_value`);
        const salespersonInput = document.getElementById(`salesperson_${timestamp}_input`);
        const documentNumberInput = document.getElementById(`doc_number_${timestamp}`);
        const totalAmountInput = document.getElementById(`

        const applyFilters = () => {
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

            if (isSaleOrder) {
                domain = [
                    ['date_order', '>=', dateFrom + ' 00:00:00'],
                    ['date_order', '<=', dateTo + ' 23:59:59']
                ];
                resModel = 'sale.order';
                views = [[false, 'list'], [false, 'form']];
            } else if (isInvoice) {
                domain = [
                    ['invoice_date', '>=', dateFrom],
                    ['invoice_date', '<=', dateTo],
                    ['move_type', '=', 'out_invoice'],
                    ['state', '!=', 'cancel']
                ];
                resModel = 'account.move';
                views = [[false, 'list'], [false, 'form']];
            }

            if (warehouseSelect && warehouseSelect.value) {
                const warehouseId = parseInt(warehouseSelect.value);
                if (isSaleOrder) {
                    domain.push(['warehouse_id', '=', warehouseId]);
                } else if (isInvoice) {
                    domain.push(['invoice_line_ids.sale_line_ids.order_id.warehouse_id', '=', warehouseId]);
                }
            }

            if (customerValue.value) {
                domain.push(['partner_id', '=', parseInt(customerValue.value)]);
            }

            if (salespersonValue.value) {
                const userId = parseInt(salespersonValue.value);
                if (isSaleOrder) {
                    domain.push(['user_id', '=', userId]);
                } else if (isInvoice) {
                    domain.push(['invoice_user_id', '=', userId]);
                }
            }

            if (documentNumberInput.value.trim()) {
                domain.push(['name', 'ilike', documentNumberInput.value.trim()]);
            }

            if (totalAmountInput.value && parseFloat(totalAmountInput.value) > 0) {
                domain.push(['amount_total', '=', parseFloat(totalAmountInput.value)]);
            }

            if (customerRefInput.value.trim()) {
                domain.push(['ref', 'ilike', customerRefInput.value.trim()]);
            }

            if (awbNumberInput.value.trim()) {
                domain.push(['awb_number', 'ilike', awbNumberInput.value.trim()]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders/Quotations' : 'Invoices',
                res_model: resModel,
                views: views,
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters applied", { type: "success" });
        };

        const clearFilters = () => {
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
            awbNumberInput.value = '';

            let domain = [];
            let resModel = '';
            let views = [];

            if (isSaleOrder) {
                domain = [];
                resModel = 'sale.order';
                views = [[false, 'list'], [false, 'form']];
            } else if (isInvoice) {
                domain = [['move_type', '=', 'out_invoice']];
                resModel = 'account.move';
                views = [[false, 'list'], [false, 'form']];
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders/Quotations' : 'Invoices',
                res_model: resModel,
                views: views,
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        this._applyFiltersCallback = applyFilters;

        this.addEventListener(applyBtn, 'click', applyFilters);
        this.addEventListener(clearBtn, 'click', clearFilters);

        // Setup autocomplete
        this.setupAutocomplete(`customer_${timestamp}`, this._filterData.customers);
        this.setupAutocomplete(`salesperson_${timestamp}`, this._filterData.salespersons);

        // Keyboard shortcuts
        const filterContainer = document.querySelector('.sale_date_filter_container');
        if (filterContainer) {
            this.addEventListener(document, 'keydown', (e) => {
                if (e.key === 'Escape') {
                    const activeElement = document.activeElement;
                    const isInAutocomplete = activeElement && activeElement.classList.contains('autocomplete-input');
                    const isDropdownOpen = document.querySelector('.autocomplete_dropdown.show');

                    if (!isInAutocomplete || !isDropdownOpen) {
                        clearFilters();
                    }
                }
            });

            const regularInputs = filterContainer.querySelectorAll('.filter-input:not(.autocomplete-input), select');
            regularInputs.forEach(input => {
                this.addEventListener(input, 'keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyFilters();
                    }
                });
            });
        }
    },
});