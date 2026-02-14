/** @odoo-module **/

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
            salespersons: [],
            analyticAccounts: []  // Added analytic accounts
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
        const domain = this.props.domain || [];

        // Check if it's a sale order
        if (resModel === 'sale.order') {
            return true;
        }

        // Check if it's a sale invoice (account.move with move_type 'out_invoice')
        if (resModel === 'account.move') {
            // Check if domain contains out_invoice filter
            const hasOutInvoiceFilter = domain.some(condition =>
                Array.isArray(condition) &&
                condition[0] === 'move_type' &&
                condition[2] === 'out_invoice'
            );

            // Check context for type indicator
            const isOutInvoiceFromContext = context.default_move_type === 'out_invoice' ||
                                           context.type === 'out_invoice';

            // If either check passes, it's a sales invoice
            return hasOutInvoiceFilter || isOutInvoiceFromContext;
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
            const [warehouses, customers, salespersons, analyticAccounts] = await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }).catch(() => []),
                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }).catch(() => []),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }).catch(() => []),
                // Load analytic accounts with reference for better display
                this.orm.searchRead('account.analytic.account', [], ['id', 'name', 'code'],
                    { limit: 500, order: 'name' }).catch(() => [])
            ]);

            this._filterData = {
                warehouses: warehouses || [],
                customers: customers || [],
                salespersons: salespersons || [],
                analyticAccounts: analyticAccounts || []
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

                        <div class="filter_group filter_group_small autocomplete_group_small">
                            <div class="autocomplete_wrapper">
                                <input type="text" class="form-control autocomplete_input_small filter_analytic_input" placeholder="Warehouse" />
                                <div class="autocomplete_dropdown filter_analytic_dropdown"></div>
                            </div>
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
                            <input type="text" class="form-control filter_input_small filter_total_amount" placeholder="Total Amount" />
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="text" class="form-control filter_input_small filter_awb_number" placeholder="AWB No" />
                        </div>

                        <div class="filter_group filter_group_small">
                            <input type="text" class="form-control filter_input_small filter_delivery_note" placeholder="Delivery Note" />
                        </div>


                        <div class="filter_actions">
                            <button class="btn btn-primary apply_filter_btn">Apply</button>
                            <button class="btn btn-secondary clear_filter_btn">Clear</button>
                        </div>
                    </div>
                </div>
            `;

            const wrapperDiv = document.createElement('div');
            wrapperDiv.className = 'sale_date_filter_wrapper_main';
            wrapperDiv.innerHTML = filterHTML;

            // Try multiple insertion strategies
            let inserted = false;

            // Strategy 1: Try to insert before listTable if it has a parent
            if (listTable.parentNode) {
                try {
                    listTable.parentNode.insertBefore(wrapperDiv, listTable);
                    inserted = true;
                } catch (e) {
                    console.debug('Strategy 1 failed:', e);
                }
            }

            // Strategy 2: Try to find .o_content and prepend
            if (!inserted) {
                const contentArea = document.querySelector('.o_content');
                if (contentArea) {
                    try {
                        contentArea.insertBefore(wrapperDiv, contentArea.firstChild);
                        inserted = true;
                    } catch (e) {
                        console.debug('Strategy 2 failed:', e);
                    }
                }
            }

            // Strategy 3: Try to find .o_list_view and prepend
            if (!inserted) {
                const listView = document.querySelector('.o_list_view');
                if (listView) {
                    try {
                        listView.insertBefore(wrapperDiv, listView.firstChild);
                        inserted = true;
                    } catch (e) {
                        console.debug('Strategy 3 failed:', e);
                    }
                }
            }

            if (!inserted) {
                console.warn('Could not insert filter - no valid insertion point found');
                return false;
            }

            this._filterInjected = true;
            this.attachFilterListeners();

            return true;
        } catch (error) {
            console.error('Error injecting filter:', error);
            return false;
        }
    },

    _getCurrentActionViews() {
        try {
            // Try to get current action's views to preserve column configuration
            const action = this.actionService?.currentController?.action;
            if (action && action.views && action.views.length > 0) {
                return action.views;
            }
        } catch (e) {
            console.debug('Could not get current action views:', e);
        }

        // Fallback: use the views from props or model-specific defaults
        if (this.props.views && this.props.views.length > 0) {
            return this.props.views;
        }

        // Last resort fallback
        return this.props.resModel === 'sale.order'
            ? [[false, 'list'], [false, 'form']]
            : [[false, 'list'], [false, 'form']];
    },

    _getCurrentActionContext() {
        try {
            // Get current action context to preserve settings
            const action = this.actionService?.currentController?.action;
            if (action && action.context) {
                return { ...action.context };
            }
        } catch (e) {
            console.debug('Could not get current action context:', e);
        }

        // Fallback to props context
        return { ...(this.props.context || {}) };
    },

    _getActionConfig() {
        // Helper to get complete action configuration
        try {
            const action = this.actionService?.currentController?.action;
            if (action) {
                return {
                    views: action.views || this._getCurrentActionViews(),
                    context: action.context || this._getCurrentActionContext(),
                    viewId: action.view_id || false,
                    searchViewId: action.search_view_id || false,
                };
            }
        } catch (e) {
            console.debug('Could not get action config:', e);
        }

        return {
            views: this._getCurrentActionViews(),
            context: this._getCurrentActionContext(),
            viewId: false,
            searchViewId: false,
        };
    },

    attachFilterListeners() {
        // Define model type flags at the beginning so they're available to all functions
        const isSaleOrder = this.props.resModel === 'sale.order';
        const isInvoice = this.props.resModel === 'account.move';
        const resModel = this.props.resModel;

        const dateFromInput = document.querySelector('.filter_date_from');
        const dateToInput = document.querySelector('.filter_date_to');
        const warehouseSelect = document.querySelector('.filter_warehouse');
        const documentNumberInput = document.querySelector('.filter_doc_number');
        const totalAmountInput = document.querySelector('.filter_total_amount');
        const customerRefInput = document.querySelector('.filter_customer_ref');
        const awbNumberInput = document.querySelector('.filter_awb_number');
        const deliveryNoteInput = document.querySelector('.filter_delivery_note');

        const customerInput = document.querySelector('.filter_customer_input');
        const customerDropdown = document.querySelector('.filter_customer_dropdown');

        const salespersonInput = document.querySelector('.filter_salesperson_input');
        const salespersonDropdown = document.querySelector('.filter_salesperson_dropdown');

        // Analytic account elements
        const analyticInput = document.querySelector('.filter_analytic_input');
        const analyticDropdown = document.querySelector('.filter_analytic_dropdown');

        const applyBtn = document.querySelector('.apply_filter_btn');
        const clearBtn = document.querySelector('.clear_filter_btn');

        let customerSelectedId = null;
        let salespersonSelectedId = null;
        let analyticSelectedId = null;  // Track selected analytic account

        // Customer autocomplete
        if (customerInput && customerDropdown) {
            this.addEventListener(customerInput, 'input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showCustomerDropdown(customerInput, customerDropdown, searchTerm);
                } else {
                    customerDropdown.classList.remove('show');
                    customerSelectedId = null;
                }
            });

            this.addEventListener(customerInput, 'focus', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showCustomerDropdown(customerInput, customerDropdown, searchTerm);
                }
            });

            this.addEventListener(customerDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    customerSelectedId = parseInt(item.dataset.id);
                    customerInput.value = item.textContent;
                    customerDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!customerInput.contains(e.target) && !customerDropdown.contains(e.target)) {
                    customerDropdown.classList.remove('show');
                }
            });
        }

        // Salesperson autocomplete
        if (salespersonInput && salespersonDropdown) {
            this.addEventListener(salespersonInput, 'input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showSalespersonDropdown(salespersonInput, salespersonDropdown, searchTerm);
                } else {
                    salespersonDropdown.classList.remove('show');
                    salespersonSelectedId = null;
                }
            });

            this.addEventListener(salespersonInput, 'focus', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showSalespersonDropdown(salespersonInput, salespersonDropdown, searchTerm);
                }
            });

            this.addEventListener(salespersonDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    salespersonSelectedId = parseInt(item.dataset.id);
                    salespersonInput.value = item.textContent;
                    salespersonDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!salespersonInput.contains(e.target) && !salespersonDropdown.contains(e.target)) {
                    salespersonDropdown.classList.remove('show');
                }
            });
        }

        // Analytic account autocomplete
        if (analyticInput && analyticDropdown) {
            this.addEventListener(analyticInput, 'input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showAnalyticDropdown(analyticInput, analyticDropdown, searchTerm);
                } else {
                    // Show all analytic accounts when input is empty
                    this.showAnalyticDropdown(analyticInput, analyticDropdown, '');
                }
            });

            this.addEventListener(analyticInput, 'focus', (e) => {
                // Always show dropdown on focus, even if empty
                const searchTerm = e.target.value.trim();
                this.showAnalyticDropdown(analyticInput, analyticDropdown, searchTerm || '');
            });

            this.addEventListener(analyticInput, 'click', (e) => {
                // Show dropdown on click as well
                const searchTerm = e.target.value.trim();
                this.showAnalyticDropdown(analyticInput, analyticDropdown, searchTerm || '');
            });

            this.addEventListener(analyticDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    analyticSelectedId = parseInt(item.dataset.id);
                    analyticInput.value = item.textContent;
                    analyticDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!analyticInput.contains(e.target) && !analyticDropdown.contains(e.target)) {
                    analyticDropdown.classList.remove('show');
                }
            });
        }

        // --- Apply filters ---
        const applyFilters = async () => {
            const dateFrom = dateFromInput?.value;
            const dateTo = dateToInput?.value;
            const warehouse = warehouseSelect?.value;
            const documentNumber = documentNumberInput?.value.trim();
            const totalAmount = totalAmountInput?.value.trim();
            const customerRef = customerRefInput?.value.trim();
            const awbNumber = awbNumberInput?.value.trim();
            const deliveryNote = deliveryNoteInput?.value.trim();

            let domain = [];
            if (isInvoice) {
                domain.push(['move_type', '=', 'out_invoice']);
            }

            // Date range filter
            if (dateFrom || dateTo) {
                const dateField = isSaleOrder ? 'date_order' : 'invoice_date';
                if (dateFrom && dateTo) {
                    domain.push([dateField, '>=', dateFrom + ' 00:00:00']);
                    domain.push([dateField, '<=', dateTo + ' 23:59:59']);
                } else if (dateFrom) {
                    domain.push([dateField, '>=', dateFrom + ' 00:00:00']);
                } else if (dateTo) {
                    domain.push([dateField, '<=', dateTo + ' 23:59:59']);
                }
            }

            // Warehouse filter
            if (warehouse) {
                if (isSaleOrder) {
                    domain.push(['warehouse_id', '=', parseInt(warehouse)]);
                } else {
                    // For invoices, search via sale orders
                    try {
                        const saleOrders = await this.orm.searchRead(
                            'sale.order',
                            [['warehouse_id', '=', parseInt(warehouse)]],
                            ['name'],
                            { limit: 500 }
                        );

                        if (saleOrders.length > 0) {
                            const soNames = saleOrders.map(so => so.name);
                            domain.push(['invoice_origin', 'in', soNames]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Warehouse filter error:', error);
                        this.notification.add("Error applying warehouse filter", { type: "danger" });
                        return;
                    }
                }
            }

            // Customer filter
            if (customerSelectedId) {
                domain.push(['partner_id', '=', customerSelectedId]);
            }

            // Salesperson filter
            if (salespersonSelectedId) {
                domain.push(['user_id', '=', salespersonSelectedId]);
            }

            // Analytic account filter
            if (analyticSelectedId) {
                if (isSaleOrder) {
                    // For sale orders, check order lines
                    try {
                        const saleLines = await this.orm.searchRead(
                            'sale.order.line',
                            [['analytic_distribution', '!=', false]],
                            ['order_id', 'analytic_distribution'],
                            { limit: 5000 }
                        );

                        const matchingSaleIds = [];
                        for (const line of saleLines) {
                            if (line.analytic_distribution) {
                                // analytic_distribution is stored as JSON object like {"1": 100}
                                const distribution = typeof line.analytic_distribution === 'string'
                                    ? JSON.parse(line.analytic_distribution)
                                    : line.analytic_distribution;

                                if (distribution[analyticSelectedId.toString()]) {
                                    matchingSaleIds.push(line.order_id[0]);
                                }
                            }
                        }

                        if (matchingSaleIds.length > 0) {
                            const uniqueSaleIds = [...new Set(matchingSaleIds)];
                            domain.push(['id', 'in', uniqueSaleIds]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Analytic account filter error:', error);
                        this.notification.add("Error applying analytic account filter", { type: "danger" });
                        return;
                    }
                } else {
                    // For invoices, check invoice lines
                    try {
                        const invoiceLines = await this.orm.searchRead(
                            'account.move.line',
                            [
                                ['move_id.move_type', '=', 'out_invoice'],
                                ['analytic_distribution', '!=', false]
                            ],
                            ['move_id', 'analytic_distribution'],
                            { limit: 5000 }
                        );

                        const matchingInvoiceIds = [];
                        for (const line of invoiceLines) {
                            if (line.analytic_distribution) {
                                const distribution = typeof line.analytic_distribution === 'string'
                                    ? JSON.parse(line.analytic_distribution)
                                    : line.analytic_distribution;

                                if (distribution[analyticSelectedId.toString()]) {
                                    matchingInvoiceIds.push(line.move_id[0]);
                                }
                            }
                        }

                        if (matchingInvoiceIds.length > 0) {
                            const uniqueInvoiceIds = [...new Set(matchingInvoiceIds)];
                            domain.push(['id', 'in', uniqueInvoiceIds]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Analytic account filter error:', error);
                        this.notification.add("Error applying analytic account filter", { type: "danger" });
                        return;
                    }
                }
            }

            // Document number filter
            if (documentNumber) {
                domain.push(['name', 'ilike', documentNumber]);
            }

            // Total amount filter
            if (totalAmount) {
                const amount = parseFloat(totalAmount);
                if (!isNaN(amount)) {
                    const amountField = isSaleOrder ? 'amount_total' : 'amount_total';
                    domain.push([amountField, '=', amount]);
                }
            }

            // Customer reference filter
            if (customerRef) {
                domain.push(['client_order_ref', 'ilike', customerRef]);
            }

            // AWB number filter
            if (awbNumber) {
                // Search directly in the awb_number field
                try {
                    domain.push(['awb_number', 'ilike', awbNumber]);
                } catch (error) {
                    console.error('AWB number filter error:', error);
                    this.notification.add("Error applying AWB filter: " + error.message, { type: "danger" });
                    return;
                }
            }

            // Delivery note filter
            if (deliveryNote) {
                // Search directly in the delivery_note_number field
                try {
                    domain.push(['delivery_note_number', 'ilike', deliveryNote]);
                } catch (error) {
                    console.error('Delivery Note filter error:', error);
                    this.notification.add("Error searching delivery notes: " + error.message, { type: "danger" });
                    return;
                }
            }

            const actionConfig = this._getActionConfig();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: resModel,
                views: actionConfig.views,
                view_id: actionConfig.viewId,
                search_view_id: actionConfig.searchViewId,
                domain: domain,
                context: actionConfig.context,
                target: 'current',
            });

            this.notification.add("Filters applied successfully", { type: "success" });
        };

        // --- Clear filters ---
        const clearFilters = () => {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

            dateFromInput.value = firstDay.toISOString().split('T')[0];
            dateToInput.value = today.toISOString().split('T')[0];

            if (warehouseSelect) warehouseSelect.value = '';
            if (customerInput) customerInput.value = '';
            if (salespersonInput) salespersonInput.value = '';
            if (analyticInput) analyticInput.value = '';
            if (documentNumberInput) documentNumberInput.value = '';
            if (totalAmountInput) totalAmountInput.value = '';
            if (customerRefInput) customerRefInput.value = '';
            if (awbNumberInput) awbNumberInput.value = '';
            if (deliveryNoteInput) deliveryNoteInput.value = '';

            customerSelectedId = null;
            salespersonSelectedId = null;
            analyticSelectedId = null;

            let domain = [];
            if (isInvoice) {
                domain = [['move_type', '=', 'out_invoice']];
            }

            const actionConfig = this._getActionConfig();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: isSaleOrder ? 'sale.order' : 'account.move',
                views: actionConfig.views,
                view_id: actionConfig.viewId,
                search_view_id: actionConfig.searchViewId,
                domain: domain,
                context: actionConfig.context,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        this.addEventListener(applyBtn, 'click', applyFilters);
        this.addEventListener(clearBtn, 'click', clearFilters);

        // Enter key on all text/number/date/select inputs
        [dateFromInput, dateToInput, warehouseSelect, documentNumberInput,
         totalAmountInput, customerRefInput, awbNumberInput, deliveryNoteInput]
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

        // Escape key to clear
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

    showAnalyticDropdown(input, dropdown, searchTerm) {
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            // Show all analytic accounts when no search term
            filtered = this._filterData.analyticAccounts;
        } else {
            // Filter by search term
            filtered = this._filterData.analyticAccounts.filter(a => {
                const nameMatch = a.name.toLowerCase().includes(lowerSearch);
                const codeMatch = a.code && a.code.toLowerCase().includes(lowerSearch);
                return nameMatch || codeMatch;
            });
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No analytic accounts found</div>';
        } else {
            dropdown.innerHTML = filtered.map(a => {
                // Display format: "CODE - Name" or just "Name" if no code
                const displayText = a.code ? `${a.code} - ${a.name}` : a.name;
                return `<div class="autocomplete_item" data-id="${a.id}" data-code="${a.code || ''}" data-name="${a.name}">${displayText}</div>`;
            }).join('');
        }

        dropdown.classList.add('show');
    },
});