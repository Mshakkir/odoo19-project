///** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");

        this._filterInjected = false;
        this._filterData = {
            warehouses: [],
            customers: [],
            salespersons: []
        };
        this._listeners = [];

        onMounted(async () => {
            if (this.shouldShowFilter()) {
                try {
                    await this.loadFilterData();
                    // Keep trying to inject until successful
                    let attempts = 0;
                    const tryInject = setInterval(async () => {
                        if (this.injectDateFilter()) {
                            clearInterval(tryInject);
                        }
                        attempts++;
                        if (attempts > 20) clearInterval(tryInject); // Stop after 20 attempts (10 seconds)
                    }, 500);
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
        const context = this.props.context || {};

        // Check if it's a sale order
        if (resModel === 'sale.order') {
            return true;
        }

        // Check if it's a sale invoice (account.move with move_type 'out_invoice')
        if (resModel === 'account.move') {
            // Check the context or domain to determine if it's a sales invoice
            // If the domain already filters for out_invoice, allow it
            if (this.props.domain) {
                const hasOutInvoiceFilter = this.props.domain.some(condition =>
                    Array.isArray(condition) &&
                    condition[0] === 'move_type' &&
                    condition[2] === 'out_invoice'
                );
                return hasOutInvoiceFilter;
            }
            // Default: don't show for account.move unless explicitly a sales invoice
            return false;
        }

        return false;
    },

    cleanupFilter() {
        // Remove all event listeners
        this._listeners.forEach(({ element, event, handler }) => {
            try {
                if (element) {
                    element.removeEventListener(event, handler);
                }
            } catch (e) {
                // Ignore errors during cleanup
            }
        });
        this._listeners = [];
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
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }).catch(() => []),
                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }).catch(() => []),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }).catch(() => [])
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
        if (this._filterInjected) {
            return true; // Already injected
        }

        const listTable = document.querySelector('.o_list_table');
        if (!listTable) {
            return false; // List table not ready yet
        }

        // Check if filter already exists
        const existingFilter = document.querySelector('.sale_date_filter_wrapper_main');
        if (existingFilter) {
            return true; // Already exists
        }

        try {
            const isSaleOrder = this.props.resModel === 'sale.order';
            const isInvoice = this.props.resModel === 'account.move';

            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const dateFrom = firstDay.toISOString().split('T')[0];
            const dateTo = today.toISOString().split('T')[0];

            const warehouseOptions = this._filterData.warehouses
                .map(w => `<option value="${w.id}">${w.name}</option>`)
                .join('');

            const filterHTML = `
                <div class="sale_date_filter_container">
                    <div class="date_filter_wrapper">
                        <div class="filter_group filter_group_small date_group_small">
                            <div class="date_input_group">
                                <input type="date" class="form-control date_input_small filter_date_from" value="${dateFrom}" />
                                <span class="date_separator">→</span>
                                <input type="date" class="form-control date_input_small filter_date_to" value="${dateTo}" />
                            </div>
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="text" class="form-control filter_input_small filter_doc_number"
                                placeholder="${isSaleOrder ? 'Sale Order' : 'Invoice'}" />
                        </div>

                        <div class="filter_group filter_group_small autocomplete_group_small">
                            <div class="autocomplete_wrapper">
                                <input type="text" class="form-control autocomplete_input_small filter_customer_input" placeholder="Customer" />
                                <div class="autocomplete_dropdown filter_customer_dropdown"></div>
                            </div>
                        </div>

                        <div class="filter_group filter_group_small">
                            <select class="form-select filter_select_small filter_warehouse">
                                <option value="">Warehouse</option>
                                ${warehouseOptions}
                            </select>
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="text" class="form-control filter_input_small filter_customer_ref" placeholder="Customer Ref" />
                        </div>

                        <div class="filter_group filter_group_small autocomplete_group_small">
                            <div class="autocomplete_wrapper">
                                <input type="text" class="form-control autocomplete_input_small filter_salesperson_input" placeholder="Salesperson" />
                                <div class="autocomplete_dropdown filter_salesperson_dropdown"></div>
                            </div>
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="number" class="form-control filter_input_small filter_total_amount" placeholder="Total Amount" step="0.01" min="0" />
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="text" class="form-control filter_input_small filter_awb_number" placeholder="AWB Number" />
                        </div>

                        <div class="filter_actions">
                            <button class="btn btn-primary apply_filter_btn filter_apply">Apply</button>
                            <button class="btn btn-secondary clear_filter_btn filter_clear">Clear</button>
                        </div>
                    </div>
                </div>
            `;

            const filterDiv = document.createElement('div');
            filterDiv.className = 'sale_date_filter_wrapper_main';
            filterDiv.innerHTML = filterHTML;

            listTable.parentElement.insertBefore(filterDiv, listTable);

            // Setup event listeners using class selectors (more reliable)
            this.setupFilterLogic(isSaleOrder, isInvoice);

            this._filterInjected = true;
            return true;
        } catch (error) {
            console.error('Error injecting filter:', error);
            return false;
        }
    },

    setupFilterLogic(isSaleOrder, isInvoice) {
        // Get elements using class selectors
        const dateFromInput = document.querySelector('.filter_date_from');
        const dateToInput = document.querySelector('.filter_date_to');
        const warehouseSelect = document.querySelector('.filter_warehouse');
        const customerInput = document.querySelector('.filter_customer_input');
        const customerDropdown = document.querySelector('.filter_customer_dropdown');
        const salespersonInput = document.querySelector('.filter_salesperson_input');
        const salespersonDropdown = document.querySelector('.filter_salesperson_dropdown');
        const documentNumberInput = document.querySelector('.filter_doc_number');
        const totalAmountInput = document.querySelector('.filter_total_amount');
        const customerRefInput = document.querySelector('.filter_customer_ref');
        const awbNumberInput = document.querySelector('.filter_awb_number');
        const applyBtn = document.querySelector('.filter_apply');
        const clearBtn = document.querySelector('.filter_clear');

        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) {
            console.error('Critical filter elements not found');
            return;
        }

        // Customer autocomplete
        let customerSelectedId = null;
        this.addEventListener(customerInput, 'focus', () => {
            this.showCustomerDropdown(customerInput, customerDropdown, '');
        });

        this.addEventListener(customerInput, 'input', (e) => {
            customerSelectedId = null;
            this.showCustomerDropdown(customerInput, customerDropdown, e.target.value);
        });

        this.addEventListener(customerDropdown, 'click', (e) => {
            const item = e.target.closest('.autocomplete_item');
            if (item) {
                customerInput.value = item.textContent;
                customerSelectedId = item.getAttribute('data-id');
                customerDropdown.classList.remove('show');
            }
        });

        // Salesperson autocomplete
        let salespersonSelectedId = null;
        this.addEventListener(salespersonInput, 'focus', () => {
            this.showSalespersonDropdown(salespersonInput, salespersonDropdown, '');
        });

        this.addEventListener(salespersonInput, 'input', (e) => {
            salespersonSelectedId = null;
            this.showSalespersonDropdown(salespersonInput, salespersonDropdown, e.target.value);
        });

        this.addEventListener(salespersonDropdown, 'click', (e) => {
            const item = e.target.closest('.autocomplete_item');
            if (item) {
                salespersonInput.value = item.textContent;
                salespersonSelectedId = item.getAttribute('data-id');
                salespersonDropdown.classList.remove('show');
            }
        });

        // Apply filters
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

            // Add optional filters
            if (warehouseSelect && warehouseSelect.value) {
                const whId = parseInt(warehouseSelect.value);
                if (isSaleOrder) {
                    domain.push(['warehouse_id', '=', whId]);
                }
            }

            if (customerSelectedId) {
                domain.push(['partner_id', '=', parseInt(customerSelectedId)]);
            }

            if (salespersonSelectedId) {
                const userId = parseInt(salespersonSelectedId);
                if (isSaleOrder) {
                    domain.push(['user_id', '=', userId]);
                }
            }

            if (documentNumberInput && documentNumberInput.value.trim()) {
                domain.push(['name', 'ilike', documentNumberInput.value.trim()]);
            }

            if (totalAmountInput && totalAmountInput.value) {
                const amount = parseFloat(totalAmountInput.value);
                if (amount > 0) {
                    domain.push(['amount_total', '=', amount]);
                }
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

            this.notification.add("Filters applied successfully", { type: "success" });
        };

        // Clear filters
        const clearFilters = () => {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

            dateFromInput.value = firstDay.toISOString().split('T')[0];
            dateToInput.value = today.toISOString().split('T')[0];

            if (warehouseSelect) warehouseSelect.value = '';
            if (customerInput) customerInput.value = '';
            if (salespersonInput) salespersonInput.value = '';
            if (documentNumberInput) documentNumberInput.value = '';
            if (totalAmountInput) totalAmountInput.value = '';
            if (customerRefInput) customerRefInput.value = '';
            if (awbNumberInput) awbNumberInput.value = '';

            customerSelectedId = null;
            salespersonSelectedId = null;

            let domain = [];
            if (isInvoice) {
                domain = [['move_type', '=', 'out_invoice']];
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: isSaleOrder ? 'sale.order' : 'account.move',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        this.addEventListener(applyBtn, 'click', applyFilters);
        this.addEventListener(clearBtn, 'click', clearFilters);

        // Enter key
        [dateFromInput, dateToInput, warehouseSelect, documentNumberInput, totalAmountInput, customerRefInput, awbNumberInput]
            .forEach(el => {
                if (el) {
                    this.addEventListener(el, 'keydown', (e) => {
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

    showCustomerDropdown(input, dropdown, searchTerm) {
        const lowerSearch = searchTerm.toLowerCase();
        const filtered = this._filterData.customers.filter(c =>
            c.name.toLowerCase().includes(lowerSearch)
        );

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No customers found</div>';
        } else {
            dropdown.innerHTML = filtered.map(c =>
                `<div class="autocomplete_item" data-id="${c.id}">${c.name}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },

    showSalespersonDropdown(input, dropdown, searchTerm) {
        const lowerSearch = searchTerm.toLowerCase();
        const filtered = this._filterData.salespersons.filter(s =>
            s.name.toLowerCase().includes(lowerSearch)
        );

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No salespersons found</div>';
        } else {
            dropdown.innerHTML = filtered.map(s =>
                `<div class="autocomplete_item" data-id="${s.id}">${s.name}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },
});