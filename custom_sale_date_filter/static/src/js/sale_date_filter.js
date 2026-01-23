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
        this._instanceId = ++filterInstanceCount;
        this._listeners = [];

        onMounted(async () => {
            if (this.shouldShowFilter()) {
                try {
                    await this.loadFilterData();
                    await this.delay(100); // Wait for DOM to settle
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

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    shouldShowFilter() {
        const resModel = this.props.resModel;
        return resModel === 'sale.order' || resModel === 'account.move';
    },

    cleanupFilter() {
        // Remove all event listeners
        this._listeners.forEach(({ element, event, handler }) => {
            if (element) {
                element.removeEventListener(event, handler);
            }
        });
        this._listeners = [];

        // Remove filter DOM
        if (this._filterElement && this._filterElement.parentNode) {
            this._filterElement.remove();
            this._filterElement = null;
        }
    },

    addEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            this._listeners.push({ element, event, handler });
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
                warehouses: warehouses || [],
                customers: customers || [],
                salespersons: salespersons || []
            };
        } catch (error) {
            console.error('Error loading filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
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

        const id = this._instanceId;
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        const isSaleOrder = this.props.resModel === 'sale.order';
        const isInvoice = this.props.resModel === 'account.move';

        const warehouseOptions = this._filterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        const filterDiv = document.createElement('div');
        filterDiv.className = 'sale_date_filter_wrapper_main';
        filterDiv.innerHTML = `
            <div class="sale_date_filter_container">
                <div class="date_filter_wrapper">
                    <div class="filter_group filter_group_small date_group_small">
                        <div class="date_input_group">
                            <input type="date" class="form-control date_input_small" id="date_from_${id}" value="${dateFrom}" />
                            <span class="date_separator">→</span>
                            <input type="date" class="form-control date_input_small" id="date_to_${id}" value="${dateTo}" />
                        </div>
                    </div>

                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small" id="doc_number_${id}"
                            placeholder="${isSaleOrder ? 'Sale Order' : 'Invoice'}" />
                    </div>

                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input type="text" class="form-control autocomplete_input_small" id="customer_${id}_input" placeholder="Customer" />
                            <input type="hidden" id="customer_${id}_value" />
                            <div class="autocomplete_dropdown" id="customer_${id}_dropdown"></div>
                        </div>
                    </div>

                    <div class="filter_group filter_group_small">
                        <select class="form-select filter_select_small" id="warehouse_${id}">
                            <option value="">Warehouse</option>
                            ${warehouseOptions}
                        </select>
                    </div>

                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small" id="customer_ref_${id}" placeholder="Customer Ref" />
                    </div>

                    <div class="filter_group filter_group_small autocomplete_group_small">
                        <div class="autocomplete_wrapper">
                            <input type="text" class="form-control autocomplete_input_small" id="salesperson_${id}_input" placeholder="Salesperson" />
                            <input type="hidden" id="salesperson_${id}_value" />
                            <div class="autocomplete_dropdown" id="salesperson_${id}_dropdown"></div>
                        </div>
                    </div>

                    <div class="filter_group filter_group_small">
                        <input type="number" class="form-control filter_input_small" id="total_amount_${id}" placeholder="Total Amount" step="0.01" min="0" />
                    </div>

                    <div class="filter_group filter_group_small">
                        <input type="text" class="form-control filter_input_small" id="awb_number_${id}" placeholder="AWB Number" />
                    </div>

                    <div class="filter_actions">
                        <button class="btn btn-primary apply_filter_btn" id="apply_filter_${id}">Apply</button>
                        <button class="btn btn-secondary clear_filter_btn" id="clear_filter_${id}">Clear</button>
                    </div>
                </div>
            </div>
        `;

        listTable.parentElement.insertBefore(filterDiv, listTable);
        this._filterElement = filterDiv;

        // Setup autocomplete
        this.setupAutocomplete(id, 'customer', this._filterData.customers);
        this.setupAutocomplete(id, 'salesperson', this._filterData.salespersons);

        // Attach filter events
        this.attachFilterEvents(id, isSaleOrder, isInvoice);
    },

    setupAutocomplete(instanceId, fieldName, dataList) {
        const inputId = `${fieldName}_${instanceId}_input`;
        const valueId = `${fieldName}_${instanceId}_value`;
        const dropdownId = `${fieldName}_${instanceId}_dropdown`;

        const input = document.getElementById(inputId);
        const hiddenValue = document.getElementById(valueId);
        const dropdown = document.getElementById(dropdownId);

        if (!input || !hiddenValue || !dropdown) {
            console.warn(`Autocomplete elements not found for ${fieldName}`);
            return;
        }

        let selectedIndex = -1;

        const showDropdown = (searchTerm = '') => {
            const lowerSearch = searchTerm.toLowerCase();
            const filtered = dataList.filter(item =>
                item.name.toLowerCase().includes(lowerSearch)
            );

            if (filtered.length === 0) {
                dropdown.innerHTML = '<div class="autocomplete_item no_results">No results</div>';
            } else {
                dropdown.innerHTML = filtered.map(item =>
                    `<div class="autocomplete_item" data-id="${item.id}" data-name="${item.name}">${item.name}</div>`
                ).join('');

                dropdown.querySelectorAll('.autocomplete_item').forEach(item => {
                    this.addEventListener(item, 'click', () => {
                        input.value = item.getAttribute('data-name');
                        hiddenValue.value = item.getAttribute('data-id');
                        dropdown.classList.remove('show');
                    });
                });
            }

            dropdown.classList.add('show');
            selectedIndex = -1;
        };

        this.addEventListener(input, 'focus', () => {
            showDropdown('');
        });

        this.addEventListener(input, 'input', (e) => {
            hiddenValue.value = '';
            showDropdown(e.target.value);
        });

        this.addEventListener(input, 'keydown', (e) => {
            const items = dropdown.querySelectorAll('.autocomplete_item:not(.no_results)');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.updateSelection(items, selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                this.updateSelection(items, selectedIndex);
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                const item = items[selectedIndex];
                input.value = item.getAttribute('data-name');
                hiddenValue.value = item.getAttribute('data-id');
                dropdown.classList.remove('show');
            } else if (e.key === 'Escape') {
                dropdown.classList.remove('show');
            }
        });

        this.addEventListener(document, 'click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    },

    updateSelection(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    },

const clearBtn = document.getElementById(`clear_filter_${instanceId}`);

        if (!fromInput || !toInput || !applyBtn || !clearBtn) {
            console.error('Filter elements not found');
            return;
        }

        const applyFilters = () => {
            const dateFrom = fromInput.value;
            const dateTo = toInput.value;

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
                const whId = parseInt(warehouseSelect.value);
                if (isSaleOrder) {
                    domain.push(['warehouse_id', '=', whId]);
                } else if (isInvoice) {
                    domain.push(['invoice_line_ids.sale_line_ids.order_id.warehouse_id', '=', whId]);
                }
            }

            if (customerValue && customerValue.value) {
                domain.push(['partner_id', '=', parseInt(customerValue.value)]);
            }

            if (salespersonValue && salespersonValue.value) {
                const userId = parseInt(salespersonValue.value);
                if (isSaleOrder) {
                    domain.push(['user_id', '=', userId]);
                } else if (isInvoice) {
                    domain.push(['invoice_user_id', '=', userId]);
                }
            }

            if (documentNumberInput && documentNumberInput.value.trim()) {
                domain.push(['name', 'ilike', documentNumberInput.value.trim()]);
            }

            if (totalAmountInput && totalAmountInput.value && parseFloat(totalAmountInput.value) > 0) {
                domain.push(['amount_total', '=', parseFloat(totalAmountInput.value)]);
            }

            if (customerRefInput && customerRefInput.value.trim()) {
                domain.push(['ref', 'ilike', customerRefInput.value.trim()]);
            }

            if (awbNumberInput && awbNumberInput.value.trim()) {
                domain.push(['awb_number', 'ilike', awbNumberInput.value.trim()]);
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
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

            fromInput.value = firstDay.toISOString().split('T')[0];
            toInput.value = today.toISOString().split('T')[0];
            if (warehouseSelect) warehouseSelect.value = '';
            if (customerInput) customerInput.value = '';
            if (customerValue) customerValue.value = '';
            if (salespersonValue) salespersonValue.value = '';
            if (documentNumberInput) documentNumberInput.value = '';
            if (totalAmountInput) totalAmountInput.value = '';
            if (customerRefInput) customerRefInput.value = '';
            if (awbNumberInput) awbNumberInput.value = '';

            let domain = [];
            let resModel = '';
            let views = [];

            if (isSaleOrder) {
                resModel = 'sale.order';
                views = [[false, 'list'], [false, 'form']];
            } else if (isInvoice) {
                domain = [['move_type', '=', 'out_invoice']];
                resModel = 'account.move';
                views = [[false, 'list'], [false, 'form']];
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: resModel,
                views: views,
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        this.addEventListener(applyBtn, 'click', applyFilters);
        this.addEventListener(clearBtn, 'click', clearFilters);

        // Enter key on inputs
        const inputs = [fromInput, toInput, warehouseSelect, documentNumberInput, totalAmountInput, customerRefInput, awbNumberInput];
        inputs.forEach(input => {
            if (input) {
                this.addEventListener(input, 'keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyFilters();
                    }
                });
            }
        });

        // Escape key
        this.addEventListener(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                clearFilters();
            }
        });
    },
});