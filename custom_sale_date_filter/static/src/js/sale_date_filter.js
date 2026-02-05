//
//
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//import { useService } from "@web/core/utils/hooks";
//import { onMounted, onWillUnmount } from "@odoo/owl";
//
//patch(ListController.prototype, {
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this.actionService = useService("action");
//        this.orm = useService("orm");
//
//        this._filterInjected = false;
//        this._filterData = {
//            warehouses: [],
//            customers: [],
//            salespersons: []
//        };
//        this._listeners = [];
//
//        onMounted(async () => {
//            if (this.shouldShowFilter()) {
//                try {
//                    await this.loadFilterData();
//                    let attempts = 0;
//                    const tryInject = setInterval(async () => {
//                        if (this.injectDateFilter()) {
//                            clearInterval(tryInject);
//                        }
//                        attempts++;
//                        if (attempts > 20) clearInterval(tryInject);
//                    }, 500);
//                } catch (error) {
//                    console.error('Filter initialization error:', error);
//                }
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupFilter();
//        });
//    },
//
//    shouldShowFilter() {
//        const resModel = this.props.resModel;
//        const context = this.props.context || {};
//        const domain = this.props.domain || [];
//
//        if (resModel === 'sale.order') {
//            return true;
//        }
//
//        if (resModel === 'account.move') {
//            const hasOutInvoiceFilter = domain.some(condition =>
//                Array.isArray(condition) &&
//                condition[0] === 'move_type' &&
//                condition[2] === 'out_invoice'
//            );
//
//            const isOutInvoiceFromContext = context.default_move_type === 'out_invoice' ||
//                                           context.type === 'out_invoice';
//
//            return hasOutInvoiceFilter || isOutInvoiceFromContext;
//        }
//
//        return false;
//    },
//
//    cleanupFilter() {
//        this._listeners.forEach(({ element, event, handler }) => {
//            try {
//                if (element) {
//                    element.removeEventListener(event, handler);
//                }
//            } catch (e) {
//                // Ignore errors during cleanup
//            }
//        });
//        this._listeners = [];
//    },
//
//    addEventListener(element, event, handler) {
//        if (element) {
//            element.addEventListener(event, handler);
//            this._listeners.push({ element, event, handler });
//        }
//    },
//
//    async loadFilterData() {
//        try {
//            const [warehouses, customers, salespersons] = await Promise.all([
//                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }).catch(() => []),
//                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name'],
//                    { limit: 500, order: 'name' }).catch(() => []),
//                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }).catch(() => [])
//            ]);
//
//            this._filterData = {
//                warehouses: warehouses || [],
//                customers: customers || [],
//                salespersons: salespersons || []
//            };
//        } catch (error) {
//            console.error('Error loading filter data:', error);
//            this.notification.add("Error loading filter options", { type: "danger" });
//        }
//    },
//
//    // ---------------------------------------------------------------
//    // FIX #2 & #3 — Capture the REAL view IDs from the current action
//    // so that doAction reuses the original list view (all columns).
//    // ---------------------------------------------------------------
//    _getCurrentActionViews() {
//        try {
//            const controller = this.actionService.currentController;
//            if (controller && controller.action && controller.action.views) {
//                return controller.action.views;   // e.g. [[123, 'list'], [456, 'form']]
//            }
//        } catch (e) {
//            // fall through
//        }
//        // Fallback: generic views (will still lose columns, but avoids crash)
//        return [[false, 'list'], [false, 'form']];
//    },
//
//    // Also grab the current action's context so filters like
//    // default_move_type survive the doAction reload.
//    _getCurrentActionContext() {
//        try {
//            const controller = this.actionService.currentController;
//            if (controller && controller.action && controller.action.context) {
//                return controller.action.context;
//            }
//        } catch (e) {
//            // fall through
//        }
//        return {};
//    },
//
//    injectDateFilter() {
//        if (this._filterInjected) {
//            return true;
//        }
//
//        const listTable = document.querySelector('.o_list_table');
//        if (!listTable) {
//            return false;
//        }
//
//        const existingFilter = document.querySelector('.sale_date_filter_wrapper_main');
//        if (existingFilter) {
//            return true;
//        }
//
//        try {
//            const isSaleOrder = this.props.resModel === 'sale.order';
//            const isInvoice = this.props.resModel === 'account.move';
//
//            const today = new Date();
//            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//            const dateFrom = firstDay.toISOString().split('T')[0];
//            const dateTo = today.toISOString().split('T')[0];
//
//            const warehouseOptions = this._filterData.warehouses
//                .map(w => `<option value="${w.id}">${w.name}</option>`)
//                .join('');
//
//            const filterHTML = `
//                <div class="sale_date_filter_container">
//                    <div class="date_filter_wrapper">
//                        <div class="filter_group filter_group_small date_group_small">
//                            <div class="date_input_group">
//                                <input type="date" class="form-control date_input_small filter_date_from" value="${dateFrom}" />
//                                <span class="date_separator">→</span>
//                                <input type="date" class="form-control date_input_small filter_date_to" value="${dateTo}" />
//                            </div>
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <input type="text" class="form-control filter_input_small filter_doc_number"
//                                placeholder="${isSaleOrder ? 'Sale Order' : 'Invoice'}" />
//                        </div>
//
//                        <div class="filter_group filter_group_small autocomplete_group_small">
//                            <div class="autocomplete_wrapper">
//                                <input type="text" class="form-control autocomplete_input_small filter_customer_input" placeholder="Customer" />
//                                <div class="autocomplete_dropdown filter_customer_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <select class="form-select filter_select_small filter_warehouse">
//                                <option value="">Warehouse</option>
//                                ${warehouseOptions}
//                            </select>
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <input type="text" class="form-control filter_input_small filter_customer_ref" placeholder="Customer Ref" />
//                        </div>
//
//                        <div class="filter_group filter_group_small autocomplete_group_small">
//                            <div class="autocomplete_wrapper">
//                                <input type="text" class="form-control autocomplete_input_small filter_salesperson_input" placeholder="Sales Rep" />
//                                <div class="autocomplete_dropdown filter_salesperson_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <input type="number" class="form-control filter_input_small filter_total_amount" placeholder="Total Amount" step="0.01" min="0" />
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <input type="text" class="form-control filter_input_small filter_awb_number" placeholder="Shipping Rep" />
//                        </div>
//
//                        <div class="filter_group filter_group_small">
//                            <input type="text" class="form-control filter_input_small filter_delivery_note" placeholder="Delivery Note" />
//                        </div>
//
//                        <div class="filter_actions">
//                            <button class="btn btn-primary apply_filter_btn filter_apply">Apply</button>
//                            <button class="btn btn-secondary clear_filter_btn filter_clear">Clear</button>
//                        </div>
//                    </div>
//                </div>
//            `;
//
//            const filterDiv = document.createElement('div');
//            filterDiv.className = 'sale_date_filter_wrapper_main';
//            filterDiv.innerHTML = filterHTML;
//
//            listTable.parentElement.insertBefore(filterDiv, listTable);
//
//            this.setupFilterLogic(isSaleOrder, isInvoice);
//
//            this._filterInjected = true;
//            return true;
//        } catch (error) {
//            console.error('Error injecting filter:', error);
//            return false;
//        }
//    },
//
//    setupFilterLogic(isSaleOrder, isInvoice) {
//        const dateFromInput = document.querySelector('.filter_date_from');
//        const dateToInput = document.querySelector('.filter_date_to');
//        const warehouseSelect = document.querySelector('.filter_warehouse');
//        const customerInput = document.querySelector('.filter_customer_input');
//        const customerDropdown = document.querySelector('.filter_customer_dropdown');
//        const salespersonInput = document.querySelector('.filter_salesperson_input');
//        const salespersonDropdown = document.querySelector('.filter_salesperson_dropdown');
//        const documentNumberInput = document.querySelector('.filter_doc_number');
//        const totalAmountInput = document.querySelector('.filter_total_amount');
//        const customerRefInput = document.querySelector('.filter_customer_ref');
//        const awbNumberInput = document.querySelector('.filter_awb_number');
//        const deliveryNoteInput = document.querySelector('.filter_delivery_note');
//        const applyBtn = document.querySelector('.filter_apply');
//        const clearBtn = document.querySelector('.filter_clear');
//
//        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) {
//            console.error('Critical filter elements not found');
//            return;
//        }
//
//        // --- Customer autocomplete ---
//        let customerSelectedId = null;
//        this.addEventListener(customerInput, 'focus', () => {
//            this.showCustomerDropdown(customerInput, customerDropdown, '');
//        });
//
//        this.addEventListener(customerInput, 'input', (e) => {
//            customerSelectedId = null;
//            this.showCustomerDropdown(customerInput, customerDropdown, e.target.value);
//        });
//
//        this.addEventListener(customerDropdown, 'click', (e) => {
//            const item = e.target.closest('.autocomplete_item');
//            if (item) {
//                customerInput.value = item.textContent;
//                customerSelectedId = item.getAttribute('data-id');
//                customerDropdown.classList.remove('show');
//            }
//        });
//
//        // --- Salesperson autocomplete ---
//        let salespersonSelectedId = null;
//        this.addEventListener(salespersonInput, 'focus', () => {
//            this.showSalespersonDropdown(salespersonInput, salespersonDropdown, '');
//        });
//
//        this.addEventListener(salespersonInput, 'input', (e) => {
//            salespersonSelectedId = null;
//            this.showSalespersonDropdown(salespersonInput, salespersonDropdown, e.target.value);
//        });
//
//        this.addEventListener(salespersonDropdown, 'click', (e) => {
//            const item = e.target.closest('.autocomplete_item');
//            if (item) {
//                salespersonInput.value = item.textContent;
//                salespersonSelectedId = item.getAttribute('data-id');
//                salespersonDropdown.classList.remove('show');
//            }
//        });
//
//        // --- Apply filters ---
//        const applyFilters = async () => {
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
//
//            if (isSaleOrder) {
//                domain = [
//                    ['date_order', '>=', dateFrom + ' 00:00:00'],
//                    ['date_order', '<=', dateTo + ' 23:59:59']
//                ];
//                resModel = 'sale.order';
//            } else if (isInvoice) {
//                domain = [
//                    ['invoice_date', '>=', dateFrom],
//                    ['invoice_date', '<=', dateTo],
//                    ['move_type', '=', 'out_invoice'],
//                    ['state', '!=', 'cancel']
//                ];
//                resModel = 'account.move';
//            }
//
//            // --- Warehouse ---
//            if (warehouseSelect && warehouseSelect.value) {
//                const whId = parseInt(warehouseSelect.value);
//                if (isSaleOrder) {
//                    domain.push(['warehouse_id', '=', whId]);
//                }
//                // For invoices, warehouse is not a direct field — skip or extend as needed.
//            }
//
//            // --- Customer ---
//            if (customerSelectedId) {
//                domain.push(['partner_id', '=', parseInt(customerSelectedId)]);
//            }
//
//            // --- Salesperson ---
//            if (salespersonSelectedId) {
//                const userId = parseInt(salespersonSelectedId);
//                if (isSaleOrder) {
//                    domain.push(['user_id', '=', userId]);
//                } else if (isInvoice) {
//                    // account.move uses invoice_user_id for the salesperson
//                    domain.push(['invoice_user_id', '=', userId]);
//                }
//            }
//
//            // --- Document number ---
//            if (documentNumberInput && documentNumberInput.value.trim()) {
//                domain.push(['name', 'ilike', documentNumberInput.value.trim()]);
//            }
//
//            // --- Total amount ---
//            if (totalAmountInput && totalAmountInput.value) {
//                const amount = parseFloat(totalAmountInput.value);
//                if (amount > 0) {
//                    domain.push(['amount_total', '=', amount]);
//                }
//            }
//
//            // --- Customer reference ---
//            if (customerRefInput && customerRefInput.value.trim()) {
//                if (isSaleOrder) {
//                    // sale.order uses client_order_ref
//                    domain.push(['client_order_ref', 'ilike', customerRefInput.value.trim()]);
//                } else if (isInvoice) {
//                    // account.move uses ref
//                    domain.push(['ref', 'ilike', customerRefInput.value.trim()]);
//                }
//            }
//
//            // --- AWB / Shipping reference ---
//            if (awbNumberInput && awbNumberInput.value.trim()) {
//                domain.push(['awb_number', 'ilike', awbNumberInput.value.trim()]);
//            }
//
//            // ---------------------------------------------------------------
//            // FIX #1 — Delivery Note filter
//            //
//            // sale.order  →  has picking_ids directly, so picking_ids.name works.
//            // account.move → does NOT have picking_ids.  We do a pre-search on
//            //                stock.picking to find matching picking IDs, then
//            //                resolve them to invoice IDs via sale_id.invoice_ids
//            //                and filter account.move by those IDs.
//            // ---------------------------------------------------------------
//            if (deliveryNoteInput && deliveryNoteInput.value.trim()) {
//                const deliverySearch = deliveryNoteInput.value.trim();
//
//                if (isSaleOrder) {
//                    // Direct traversal works on sale.order
//                    domain.push(['picking_ids.name', 'ilike', deliverySearch]);
//                } else if (isInvoice) {
//                    try {
//                        // Step 1: find stock.picking records matching the delivery note name
//                        const pickings = await this.orm.searchRead(
//                            'stock.picking',
//                            [['name', 'ilike', deliverySearch]],
//                            ['id', 'sale_id'],
//                            { limit: 200 }
//                        );
//
//                        // Step 2: collect the sale order IDs linked to those pickings
//                        const saleIds = [...new Set(
//                            pickings
//                                .filter(p => p.sale_id)
//                                .map(p => p.sale_id[0])
//                        )];
//
//                        if (saleIds.length > 0) {
//                            // Step 3: find invoices that originated from those sale orders
//                            const invoices = await this.orm.searchRead(
//                                'account.move',
//                                [
//                                    ['move_type', '=', 'out_invoice'],
//                                    ['invoice_origin', 'in', saleIds.map(String)]
//                                ],
//                                ['id'],
//                                { limit: 500 }
//                            );
//
//                            // Fallback: also try matching invoice_origin directly with
//                            // the sale order names (invoice_origin stores the SO reference string)
//                            const saleOrders = await this.orm.searchRead(
//                                'sale.order',
//                                [['id', 'in', saleIds]],
//                                ['name'],
//                                { limit: 200 }
//                            );
//                            const soNames = saleOrders.map(so => so.name);
//
//                            const invoicesByOrigin = await this.orm.searchRead(
//                                'account.move',
//                                [
//                                    ['move_type', '=', 'out_invoice'],
//                                    ['invoice_origin', 'in', soNames]
//                                ],
//                                ['id'],
//                                { limit: 500 }
//                            );
//
//                            // Merge both result sets
//                            const allInvoiceIds = [...new Set([
//                                ...invoices.map(i => i.id),
//                                ...invoicesByOrigin.map(i => i.id)
//                            ])];
//
//                            if (allInvoiceIds.length > 0) {
//                                domain.push(['id', 'in', allInvoiceIds]);
//                            } else {
//                                // No matching invoices — force empty result
//                                domain.push(['id', '=', -1]);
//                            }
//                        } else {
//                            // No sale orders found from those pickings — force empty result
//                            domain.push(['id', '=', -1]);
//                        }
//                    } catch (error) {
//                        console.error('Delivery Note pre-search error:', error);
//                        this.notification.add("Error searching delivery notes", { type: "danger" });
//                        return;  // abort apply on error
//                    }
//                }
//            }
//
//            // ---------------------------------------------------------------
//            // FIX #2 & #3 — Use the CURRENT action's real view IDs and context
//            // so doAction reloads the exact same list view (all columns intact).
//            // ---------------------------------------------------------------
//            const currentViews   = this._getCurrentActionViews();
//            const currentContext = this._getCurrentActionContext();
//
//            this.actionService.doAction({
//                type: 'ir.actions.act_window',
//                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
//                res_model: resModel,
//                views: currentViews,
//                domain: domain,
//                context: currentContext,
//                target: 'current',
//            });
//
//            this.notification.add("Filters applied successfully", { type: "success" });
//        };
//
//        // --- Clear filters ---
//        const clearFilters = () => {
//            const today = new Date();
//            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//
//            dateFromInput.value = firstDay.toISOString().split('T')[0];
//            dateToInput.value = today.toISOString().split('T')[0];
//
//            if (warehouseSelect) warehouseSelect.value = '';
//            if (customerInput) customerInput.value = '';
//            if (salespersonInput) salespersonInput.value = '';
//            if (documentNumberInput) documentNumberInput.value = '';
//            if (totalAmountInput) totalAmountInput.value = '';
//            if (customerRefInput) customerRefInput.value = '';
//            if (awbNumberInput) awbNumberInput.value = '';
//            if (deliveryNoteInput) deliveryNoteInput.value = '';
//
//            customerSelectedId = null;
//            salespersonSelectedId = null;
//
//            let domain = [];
//            if (isInvoice) {
//                domain = [['move_type', '=', 'out_invoice']];
//            }
//
//            const currentViews   = this._getCurrentActionViews();
//            const currentContext = this._getCurrentActionContext();
//
//            this.actionService.doAction({
//                type: 'ir.actions.act_window',
//                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
//                res_model: isSaleOrder ? 'sale.order' : 'account.move',
//                views: currentViews,
//                domain: domain,
//                context: currentContext,
//                target: 'current',
//            });
//
//            this.notification.add("Filters cleared", { type: "info" });
//        };
//
//        this.addEventListener(applyBtn, 'click', applyFilters);
//        this.addEventListener(clearBtn, 'click', clearFilters);
//
//        // Enter key on all text/number/date/select inputs
//        [dateFromInput, dateToInput, warehouseSelect, documentNumberInput,
//         totalAmountInput, customerRefInput, awbNumberInput, deliveryNoteInput]
//            .forEach(el => {
//                if (el) {
//                    this.addEventListener(el, 'keydown', (e) => {
//                        if (e.key === 'Enter') {
//                            e.preventDefault();
//                            applyFilters();
//                        }
//                    });
//                }
//            });
//
//        // Escape key to clear
//        this.addEventListener(document, 'keydown', (e) => {
//            if (e.key === 'Escape') {
//                clearFilters();
//            }
//        });
//    },
//
//    showCustomerDropdown(input, dropdown, searchTerm) {
//        const lowerSearch = searchTerm.toLowerCase();
//        const filtered = this._filterData.customers.filter(c =>
//            c.name.toLowerCase().includes(lowerSearch)
//        );
//
//        if (filtered.length === 0) {
//            dropdown.innerHTML = '<div class="autocomplete_item no_results">No customers found</div>';
//        } else {
//            dropdown.innerHTML = filtered.map(c =>
//                `<div class="autocomplete_item" data-id="${c.id}">${c.name}</div>`
//            ).join('');
//        }
//
//        dropdown.classList.add('show');
//    },
//
//    showSalespersonDropdown(input, dropdown, searchTerm) {
//        const lowerSearch = searchTerm.toLowerCase();
//        const filtered = this._filterData.salespersons.filter(s =>
//            s.name.toLowerCase().includes(lowerSearch)
//        );
//
//        if (filtered.length === 0) {
//            dropdown.innerHTML = '<div class="autocomplete_item no_results">No salespersons found</div>';
//        } else {
//            dropdown.innerHTML = filtered.map(s =>
//                `<div class="autocomplete_item" data-id="${s.id}">${s.name}</div>`
//            ).join('');
//        }
//
//        dropdown.classList.add('show');
//    },
//});

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
            analyticAccounts: [],  // Changed from warehouses to analyticAccounts
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
                        if (attempts > 20) clearInterval(tryInject);
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

        if (resModel === 'sale.order') {
            return true;
        }

        if (resModel === 'account.move') {
            const hasOutInvoiceFilter = domain.some(condition =>
                Array.isArray(condition) &&
                condition[0] === 'move_type' &&
                condition[2] === 'out_invoice'
            );

            const isOutInvoiceFromContext = context.default_move_type === 'out_invoice' ||
                                           context.type === 'out_invoice';

            return hasOutInvoiceFilter || isOutInvoiceFromContext;
        }

        return false;
    },

    cleanupFilter() {
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
            // Changed: Load analytic accounts instead of warehouses
            const [analyticAccounts, customers, salespersons] = await Promise.all([
                this.orm.searchRead(
                    'account.analytic.account',
                    [],
                    ['id', 'name'],
                    { limit: 100, order: 'name' }
                ).catch(() => []),
                this.orm.searchRead(
                    'res.partner',
                    [['customer_rank', '>', 0]],
                    ['id', 'name'],
                    { limit: 500, order: 'name' }
                ).catch(() => []),
                this.orm.searchRead(
                    'res.users',
                    [],
                    ['id', 'name'],
                    { limit: 100, order: 'name' }
                ).catch(() => [])
            ]);

            this._filterData = {
                analyticAccounts: analyticAccounts || [],  // Changed from warehouses
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
            return true;
        }

        const listTable = document.querySelector('.o_list_table');
        if (!listTable) {
            return false;
        }

        const existingFilter = document.querySelector('.sale_date_filter_wrapper_main');
        if (existingFilter) {
            return true;
        }

        try {
            const isSaleOrder = this.props.resModel === 'sale.order';
            const isInvoice = this.props.resModel === 'account.move';

            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const dateFrom = firstDay.toISOString().split('T')[0];
            const dateTo = today.toISOString().split('T')[0];

            // Changed: Generate analytic account options instead of warehouse
            const analyticAccountOptions = this._filterData.analyticAccounts
                .map(a => `<option value="${a.id}">${a.name}</option>`)
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
                            <select class="form-select filter_select_small filter_analytic_account">
                                <option value="">Analytic Account</option>
                                ${analyticAccountOptions}
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
                            <input type="text" class="form-control filter_input_small filter_awb_number" placeholder="Shipping Ref" />
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

            const wrapper = document.createElement('div');
            wrapper.className = 'sale_date_filter_wrapper_main';
            wrapper.innerHTML = filterHTML;

            const contentPanel = listTable.closest('.o_content');
            if (contentPanel) {
                contentPanel.insertBefore(wrapper, listTable);
            } else {
                listTable.parentNode.insertBefore(wrapper, listTable);
            }

            this._filterInjected = true;
            this.attachFilterEvents();
            return true;
        } catch (error) {
            console.error('Filter injection error:', error);
            return false;
        }
    },

    _getCurrentActionViews() {
        try {
            const actionId = this.env.config.actionId;
            if (!actionId) return [[false, 'list']];

            const action = this.env.services.action.currentController?.action;
            if (action && action.views) {
                return action.views;
            }

            return [[false, 'list']];
        } catch (error) {
            console.error('Error getting current action views:', error);
            return [[false, 'list']];
        }
    },

    _getCurrentActionContext() {
        try {
            const action = this.env.services.action.currentController?.action;
            if (action && action.context) {
                return action.context;
            }
            return this.props.context || {};
        } catch (error) {
            console.error('Error getting current action context:', error);
            return this.props.context || {};
        }
    },

    attachFilterEvents() {
        const dateFromInput = document.querySelector('.filter_date_from');
        const dateToInput = document.querySelector('.filter_date_to');
        const analyticAccountSelect = document.querySelector('.filter_analytic_account');  // Changed
        const customerInput = document.querySelector('.filter_customer_input');
        const customerDropdown = document.querySelector('.filter_customer_dropdown');
        const salespersonInput = document.querySelector('.filter_salesperson_input');
        const salespersonDropdown = document.querySelector('.filter_salesperson_dropdown');
        const documentNumberInput = document.querySelector('.filter_doc_number');
        const customerRefInput = document.querySelector('.filter_customer_ref');
        const awbNumberInput = document.querySelector('.filter_awb_number');
        const deliveryNoteInput = document.querySelector('.filter_delivery_note');
        const applyBtn = document.querySelector('.apply_filter_btn');
        const clearBtn = document.querySelector('.clear_filter_btn');

        let customerSelectedId = null;
        let salespersonSelectedId = null;

        // Customer autocomplete
        if (customerInput && customerDropdown) {
            this.addEventListener(customerInput, 'input', (e) => {
                const searchTerm = e.target.value;
                if (searchTerm.length >= 1) {
                    this.showCustomerDropdown(customerInput, customerDropdown, searchTerm);
                } else {
                    customerDropdown.classList.remove('show');
                }
                customerSelectedId = null;
            });

            this.addEventListener(customerDropdown, 'click', (e) => {
                if (e.target.classList.contains('autocomplete_item') &&
                    !e.target.classList.contains('no_results')) {
                    const id = parseInt(e.target.dataset.id);
                    const name = e.target.textContent;
                    customerInput.value = name;
                    customerSelectedId = id;
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
                const searchTerm = e.target.value;
                if (searchTerm.length >= 1) {
                    this.showSalespersonDropdown(salespersonInput, salespersonDropdown, searchTerm);
                } else {
                    salespersonDropdown.classList.remove('show');
                }
                salespersonSelectedId = null;
            });

            this.addEventListener(salespersonDropdown, 'click', (e) => {
                if (e.target.classList.contains('autocomplete_item') &&
                    !e.target.classList.contains('no_results')) {
                    const id = parseInt(e.target.dataset.id);
                    const name = e.target.textContent;
                    salespersonInput.value = name;
                    salespersonSelectedId = id;
                    salespersonDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!salespersonInput.contains(e.target) && !salespersonDropdown.contains(e.target)) {
                    salespersonDropdown.classList.remove('show');
                }
            });
        }

        // Apply filters
        const applyFilters = async () => {
            const isSaleOrder = this.props.resModel === 'sale.order';
            const isInvoice = this.props.resModel === 'account.move';
            const resModel = this.props.resModel;

            let domain = [];

            if (isInvoice) {
                domain.push(['move_type', '=', 'out_invoice']);
            }

            // Date filter
            const dateFrom = dateFromInput?.value;
            const dateTo = dateToInput?.value;
            if (dateFrom && dateTo) {
                const dateField = isSaleOrder ? 'date_order' : 'invoice_date';
                domain.push([dateField, '>=', dateFrom]);
                domain.push([dateField, '<=', dateTo]);
            }

            // Document number filter
            const docNumber = documentNumberInput?.value?.trim();
            if (docNumber) {
                domain.push(['name', 'ilike', docNumber]);
            }

            // Customer filter
            if (customerSelectedId) {
                domain.push(['partner_id', '=', customerSelectedId]);
            }

            // CHANGED: Analytic Account filter
            const analyticAccountId = analyticAccountSelect?.value;
            if (analyticAccountId) {
                if (isSaleOrder) {
                    // For sale orders: filter by analytic_account_id on order lines
                    const saleOrders = await this.orm.searchRead(
                        'sale.order.line',
                        [['analytic_distribution', '!=', false]],
                        ['order_id', 'analytic_distribution'],
                        { limit: 1000 }
                    );

                    const matchingOrderIds = [];
                    for (const line of saleOrders) {
                        if (line.analytic_distribution) {
                            const analyticIds = Object.keys(line.analytic_distribution).map(id => parseInt(id));
                            if (analyticIds.includes(parseInt(analyticAccountId))) {
                                matchingOrderIds.push(line.order_id[0]);
                            }
                        }
                    }

                    if (matchingOrderIds.length > 0) {
                        domain.push(['id', 'in', [...new Set(matchingOrderIds)]]);
                    } else {
                        domain.push(['id', '=', -1]);
                    }
                } else if (isInvoice) {
                    // For invoices: filter by analytic_account_id computed field
                    domain.push(['analytic_account_id', '=', parseInt(analyticAccountId)]);
                }
            }

            // Customer reference filter
            const customerRef = customerRefInput?.value?.trim();
            if (customerRef) {
                domain.push(['client_order_ref', 'ilike', customerRef]);
            }

            // Salesperson filter
            if (salespersonSelectedId) {
                const userField = isSaleOrder ? 'user_id' : 'invoice_user_id';
                domain.push([userField, '=', salespersonSelectedId]);
            }

            // AWB/Shipping reference filter
            const awbNumber = awbNumberInput?.value?.trim();
            if (awbNumber) {
                domain.push(['awb_number', 'ilike', awbNumber]);
            }

            // Delivery note filter
            const deliveryNote = deliveryNoteInput?.value?.trim();
            if (deliveryNote) {
                if (isSaleOrder) {
                    try {
                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            [['origin', 'ilike', deliveryNote]],
                            ['sale_id'],
                            { limit: 200 }
                        );

                        const saleIds = [...new Set(
                            pickings
                                .filter(p => p.sale_id)
                                .map(p => p.sale_id[0])
                        )];

                        if (saleIds.length > 0) {
                            domain.push(['id', 'in', saleIds]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Delivery Note search error:', error);
                        this.notification.add("Error searching delivery notes", { type: "danger" });
                        return;
                    }
                } else if (isInvoice) {
                    try {
                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            [['origin', 'ilike', deliveryNote]],
                            ['sale_id'],
                            { limit: 200 }
                        );

                        const saleIds = [...new Set(
                            pickings
                                .filter(p => p.sale_id)
                                .map(p => p.sale_id[0])
                        )];

                        if (saleIds.length > 0) {
                            const invoices = await this.orm.searchRead(
                                'account.move',
                                [
                                    ['move_type', '=', 'out_invoice'],
                                    ['invoice_origin', 'in', saleIds.map(String)]
                                ],
                                ['id'],
                                { limit: 500 }
                            );

                            const saleOrders = await this.orm.searchRead(
                                'sale.order',
                                [['id', 'in', saleIds]],
                                ['name'],
                                { limit: 200 }
                            );
                            const soNames = saleOrders.map(so => so.name);

                            const invoicesByOrigin = await this.orm.searchRead(
                                'account.move',
                                [
                                    ['move_type', '=', 'out_invoice'],
                                    ['invoice_origin', 'in', soNames]
                                ],
                                ['id'],
                                { limit: 500 }
                            );

                            const allInvoiceIds = [...new Set([
                                ...invoices.map(i => i.id),
                                ...invoicesByOrigin.map(i => i.id)
                            ])];

                            if (allInvoiceIds.length > 0) {
                                domain.push(['id', 'in', allInvoiceIds]);
                            } else {
                                domain.push(['id', '=', -1]);
                            }
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Delivery Note pre-search error:', error);
                        this.notification.add("Error searching delivery notes", { type: "danger" });
                        return;
                    }
                }
            }

            const currentViews = this._getCurrentActionViews();
            const currentContext = this._getCurrentActionContext();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: resModel,
                views: currentViews,
                domain: domain,
                context: currentContext,
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

            if (analyticAccountSelect) analyticAccountSelect.value = '';  // Changed
            if (customerInput) customerInput.value = '';
            if (salespersonInput) salespersonInput.value = '';
            if (documentNumberInput) documentNumberInput.value = '';
            if (customerRefInput) customerRefInput.value = '';
            if (awbNumberInput) awbNumberInput.value = '';
            if (deliveryNoteInput) deliveryNoteInput.value = '';

            customerSelectedId = null;
            salespersonSelectedId = null;

            const isSaleOrder = this.props.resModel === 'sale.order';
            const isInvoice = this.props.resModel === 'account.move';

            let domain = [];
            if (isInvoice) {
                domain = [['move_type', '=', 'out_invoice']];
            }

            const currentViews = this._getCurrentActionViews();
            const currentContext = this._getCurrentActionContext();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isSaleOrder ? 'Sale Orders' : 'Invoices',
                res_model: isSaleOrder ? 'sale.order' : 'account.move',
                views: currentViews,
                domain: domain,
                context: currentContext,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        this.addEventListener(applyBtn, 'click', applyFilters);
        this.addEventListener(clearBtn, 'click', clearFilters);

        // Enter key on inputs
        [dateFromInput, dateToInput, analyticAccountSelect, documentNumberInput,
         customerRefInput, awbNumberInput, deliveryNoteInput]
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
});