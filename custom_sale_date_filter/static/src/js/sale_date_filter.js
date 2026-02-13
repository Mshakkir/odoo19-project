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
            analyticAccounts: []
        };
        this._listeners = [];

        onMounted(async () => {
            if (this.shouldShowFilter()) {
                try {
                    await this.loadFilterData();
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
            const [warehouses, customers, salespersons, analyticAccounts] = await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }).catch(() => []),
                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }).catch(() => []),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }).catch(() => []),
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

            const warehouseOptions = this._filterData.warehouses
                .map(w => `<option value="${w.id}">${w.name}</option>`)
                .join('');

            const filterHTML = `
                <div class="sale_date_filter_wrapper_main">
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
                                <input type="text" class="form-control filter_input_small filter_customer_ref" placeholder="Customer Ref" />
                            </div>

                            <div class="filter_group filter_group_small autocomplete_group_small">
                                <div class="autocomplete_wrapper">
                                    <input type="text" class="form-control autocomplete_input_small filter_salesperson_input" placeholder="Salesperson" />
                                    <div class="autocomplete_dropdown filter_salesperson_dropdown"></div>
                                </div>
                            </div>

                            <div class="filter_group filter_group_small autocomplete_group_small">
                                <div class="autocomplete_wrapper">
                                    <input type="text" class="form-control autocomplete_input_small filter_analytic_input" placeholder="Analytic Account" />
                                    <div class="autocomplete_dropdown filter_analytic_dropdown"></div>
                                </div>
                            </div>

                            <div class="filter_group filter_group_small">
                                <input type="number" step="0.01" class="form-control filter_input_small filter_total_amount" placeholder="Total Amount" />
                            </div>

                            <div class="filter_group filter_group_small">
                                <input type="text" class="form-control filter_input_small filter_awb_number" placeholder="AWB Number" />
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
                </div>
            `;

            const wrapper = document.createElement('div');
            wrapper.innerHTML = filterHTML;
            const filterElement = wrapper.firstElementChild;

            const contentArea = listTable.closest('.o_content');
            if (contentArea) {
                contentArea.insertBefore(filterElement, listTable);
            } else {
                listTable.parentNode.insertBefore(filterElement, listTable);
            }

            this.attachFilterEvents();
            this._filterInjected = true;
            return true;

        } catch (error) {
            console.error('Error injecting filter:', error);
            return false;
        }
    },

    _getActionConfig() {
        const resModel = this.props.resModel;
        const context = this.props.context || {};
        const isSaleOrder = resModel === 'sale.order';

        return {
            views: isSaleOrder ? [[false, 'list'], [false, 'form']] : [[false, 'tree'], [false, 'form']],
            viewId: false,
            searchViewId: false,
            context: isSaleOrder ? { ...context } : { ...context, default_move_type: 'out_invoice' }
        };
    },

    attachFilterEvents() {
        const dateFromInput = document.querySelector('.filter_date_from');
        const dateToInput = document.querySelector('.filter_date_to');
        const warehouseSelect = document.querySelector('.filter_warehouse');
        const documentNumberInput = document.querySelector('.filter_doc_number');
        const totalAmountInput = document.querySelector('.filter_total_amount');
        const customerRefInput = document.querySelector('.filter_customer_ref');
        const awbNumberInput = document.querySelector('.filter_awb_number');
        const deliveryNoteInput = document.querySelector('.filter_delivery_note');
        const applyBtn = document.querySelector('.apply_filter_btn');
        const clearBtn = document.querySelector('.clear_filter_btn');

        // Autocomplete inputs
        const customerInput = document.querySelector('.filter_customer_input');
        const customerDropdown = document.querySelector('.filter_customer_dropdown');
        const salespersonInput = document.querySelector('.filter_salesperson_input');
        const salespersonDropdown = document.querySelector('.filter_salesperson_dropdown');
        const analyticInput = document.querySelector('.filter_analytic_input');
        const analyticDropdown = document.querySelector('.filter_analytic_dropdown');

        let customerSelectedId = null;
        let salespersonSelectedId = null;
        let analyticSelectedId = null;

        // Customer autocomplete
        if (customerInput && customerDropdown) {
            this.addEventListener(customerInput, 'focus', () => {
                this.showCustomerDropdown(customerInput, customerDropdown, customerInput.value);
            });

            this.addEventListener(customerInput, 'input', (e) => {
                customerSelectedId = null;
                this.showCustomerDropdown(customerInput, customerDropdown, e.target.value);
            });

            this.addEventListener(customerDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    customerSelectedId = parseInt(item.dataset.id);
                    customerInput.value = item.textContent.trim();
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
            this.addEventListener(salespersonInput, 'focus', () => {
                this.showSalespersonDropdown(salespersonInput, salespersonDropdown, salespersonInput.value);
            });

            this.addEventListener(salespersonInput, 'input', (e) => {
                salespersonSelectedId = null;
                this.showSalespersonDropdown(salespersonInput, salespersonDropdown, e.target.value);
            });

            this.addEventListener(salespersonDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    salespersonSelectedId = parseInt(item.dataset.id);
                    salespersonInput.value = item.textContent.trim();
                    salespersonDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!salespersonInput.contains(e.target) && !salespersonDropdown.contains(e.target)) {
                    salespersonDropdown.classList.remove('show');
                }
            });
        }

        // Analytic autocomplete
        if (analyticInput && analyticDropdown) {
            this.addEventListener(analyticInput, 'focus', () => {
                this.showAnalyticDropdown(analyticInput, analyticDropdown, analyticInput.value);
            });

            this.addEventListener(analyticInput, 'input', (e) => {
                analyticSelectedId = null;
                this.showAnalyticDropdown(analyticInput, analyticDropdown, e.target.value);
            });

            this.addEventListener(analyticDropdown, 'click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    analyticSelectedId = parseInt(item.dataset.id);
                    const code = item.dataset.code;
                    const name = item.dataset.name;
                    analyticInput.value = code ? `${code} - ${name}` : name;
                    analyticDropdown.classList.remove('show');
                }
            });

            this.addEventListener(document, 'click', (e) => {
                if (!analyticInput.contains(e.target) && !analyticDropdown.contains(e.target)) {
                    analyticDropdown.classList.remove('show');
                }
            });
        }

        const isSaleOrder = this.props.resModel === 'sale.order';
        const isInvoice = this.props.resModel === 'account.move';
        const resModel = this.props.resModel;

        // Apply filters
        const applyFilters = async () => {
            const dateFrom = dateFromInput.value;
            const dateTo = dateToInput.value;
            const warehouse = warehouseSelect ? warehouseSelect.value : '';
            const documentNumber = documentNumberInput ? documentNumberInput.value.trim() : '';
            const totalAmount = totalAmountInput ? totalAmountInput.value.trim() : '';
            const customerRef = customerRefInput ? customerRefInput.value.trim() : '';
            const awbNumber = awbNumberInput ? awbNumberInput.value.trim() : '';
            const deliveryNote = deliveryNoteInput ? deliveryNoteInput.value.trim() : '';

            let domain = [];

            if (isInvoice) {
                domain.push(['move_type', '=', 'out_invoice']);
            }

            // Date filter
            const dateField = isSaleOrder ? 'date_order' : 'invoice_date';
            if (dateFrom) {
                domain.push([dateField, '>=', dateFrom]);
            }
            if (dateTo) {
                domain.push([dateField, '<=', dateTo]);
            }

            // Warehouse filter
            if (warehouse) {
                domain.push(['warehouse_id', '=', parseInt(warehouse)]);
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
                    domain.push(['analytic_account_id', '=', analyticSelectedId]);
                } else {
                    domain.push(['line_ids.analytic_distribution', 'ilike', analyticSelectedId]);
                }
            }

            // Document number filter
            if (documentNumber) {
                domain.push(['name', 'ilike', documentNumber]);
            }

            // Total amount filter
            if (totalAmount) {
                const amountFloat = parseFloat(totalAmount);
                if (!isNaN(amountFloat)) {
                    const field = isSaleOrder ? 'amount_total' : 'amount_total';
                    domain.push([field, '>=', amountFloat - 0.01]);
                    domain.push([field, '<=', amountFloat + 0.01]);
                }
            }

            // Customer reference filter
            if (customerRef) {
                domain.push(['client_order_ref', 'ilike', customerRef]);
            }

            // AWB Number filter - FIXED VERSION
            if (awbNumber) {
                if (isSaleOrder) {
                    try {
                        // Search in stock.picking for AWB number
                        // Try multiple possible field names for AWB/tracking reference
                        const pickingDomain = ['|', '|',
                            ['carrier_tracking_ref', 'ilike', awbNumber],
                            ['name', 'ilike', awbNumber],
                            ['origin', 'ilike', awbNumber]
                        ];

                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            pickingDomain,
                            ['sale_id', 'origin'],
                            { limit: 500 }
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
                        console.error('AWB number filter error:', error);
                        this.notification.add("Error applying AWB filter: " + error.message, { type: "danger" });
                        return;
                    }
                } else {
                    // For invoices, find pickings then trace to invoices
                    try {
                        const pickingDomain = ['|', '|',
                            ['carrier_tracking_ref', 'ilike', awbNumber],
                            ['name', 'ilike', awbNumber],
                            ['origin', 'ilike', awbNumber]
                        ];

                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            pickingDomain,
                            ['sale_id', 'origin'],
                            { limit: 500 }
                        );

                        const saleIds = [...new Set(
                            pickings
                                .filter(p => p.sale_id)
                                .map(p => p.sale_id[0])
                        )];

                        if (saleIds.length > 0) {
                            // Get sale order names
                            const saleOrders = await this.orm.searchRead(
                                'sale.order',
                                [['id', 'in', saleIds]],
                                ['name'],
                                { limit: 500 }
                            );
                            const soNames = saleOrders.map(so => so.name);

                            // Find invoices with these sale order names in invoice_origin
                            domain.push(['invoice_origin', 'in', soNames]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('AWB number invoice filter error:', error);
                        this.notification.add("Error applying AWB filter: " + error.message, { type: "danger" });
                        return;
                    }
                }
            }

            // Delivery Note filter - FIXED VERSION
            if (deliveryNote) {
                if (isSaleOrder) {
                    try {
                        // Search for delivery/picking by name
                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            [['name', 'ilike', deliveryNote]],
                            ['sale_id', 'origin'],
                            { limit: 500 }
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
                        console.error('Delivery Note filter error:', error);
                        this.notification.add("Error searching delivery notes: " + error.message, { type: "danger" });
                        return;
                    }
                } else {
                    // For invoices
                    try {
                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            [['name', 'ilike', deliveryNote]],
                            ['sale_id', 'origin'],
                            { limit: 500 }
                        );

                        const saleIds = [...new Set(
                            pickings
                                .filter(p => p.sale_id)
                                .map(p => p.sale_id[0])
                        )];

                        if (saleIds.length > 0) {
                            // Get sale order names
                            const saleOrders = await this.orm.searchRead(
                                'sale.order',
                                [['id', 'in', saleIds]],
                                ['name'],
                                { limit: 500 }
                            );
                            const soNames = saleOrders.map(so => so.name);

                            // Find invoices by invoice_origin
                            domain.push(['invoice_origin', 'in', soNames]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Delivery Note invoice filter error:', error);
                        this.notification.add("Error searching delivery notes: " + error.message, { type: "danger" });
                        return;
                    }
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

        // Clear filters
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

        // Enter key on all inputs
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
            filtered = this._filterData.analyticAccounts;
        } else {
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
                const displayText = a.code ? `${a.code} - ${a.name}` : a.name;
                return `<div class="autocomplete_item" data-id="${a.id}" data-code="${a.code || ''}" data-name="${a.name}">${displayText}</div>`;
            }).join('');
        }

        dropdown.classList.add('show');
    },
});