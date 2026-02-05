///** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Patch ListController to inject date filter for Purchase Orders, RFQs and Bills
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this._purchaseFilterElement = null;
        this._purchaseFilterData = {
            warehouses: [],
            vendors: [],
            purchaseReps: [],
            analyticAccounts: []
        };

        onMounted(() => {
            if (this.shouldShowPurchaseFilter()) {
                setTimeout(() => this.loadPurchaseFilterData(), 150);
            }
        });

        onWillUnmount(() => {
            this.cleanupPurchaseFilter();
        });
    },

    shouldShowPurchaseFilter() {
        const resModel = this.props.resModel;

        // Check if it's Purchase Orders or RFQs
        if (resModel === 'purchase.order') {
            const action = this.env.config;

            // RFQ action
            if (action.xmlId === 'purchase.purchase_rfq') {
                return true;
            }

            // Purchase Order action
            if (action.xmlId === 'purchase.purchase_form_action') {
                return true;
            }

            // Check action name
            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('purchase') || actionName.includes('rfq') || actionName.includes('request for quotation')) {
                    return true;
                }
            }

            // Check domain for purchase states
            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('state') &&
                    (domainStr.includes('purchase') || domainStr.includes('done') ||
                     domainStr.includes('draft') || domainStr.includes('sent'))) {
                    return true;
                }
            }

            return true; // Show for all purchase.order views
        }

        // Check if it's Vendor Bills (account.move with in_invoice)
        if (resModel === 'account.move') {
            const action = this.env.config;

            if (action.xmlId === 'account.action_move_in_invoice_type' ||
                action.xmlId === 'purchase.action_vendor_bill_template') {
                return true;
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('bill') ||
                    (actionName.includes('vendor') && actionName.includes('invoice'))) {
                    return true;
                }
            }

            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('move_type') &&
                    domainStr.includes('in_invoice')) {
                    return true;
                }
            }
        }

        return false;
    },

    cleanupPurchaseFilter() {
        if (this._purchaseFilterElement && this._purchaseFilterElement.parentNode) {
            this._purchaseFilterElement.remove();
            this._purchaseFilterElement = null;
        }
    },

    async loadPurchaseFilterData() {
        try {
            // Load warehouses
            const warehouses = await this.orm.searchRead(
                'stock.warehouse',
                [],
                ['id', 'name'],
                { limit: 100 }
            );

            // Load vendors (partners that are suppliers)
            const vendors = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name'],
                { limit: 500, order: 'name' }
            );

            // Load purchase representatives (users)
            const purchaseReps = await this.orm.searchRead(
                'res.users',
                [],
                ['id', 'name'],
                { limit: 100, order: 'name' }
            );

            // Load analytic accounts
            const analyticAccounts = await this.orm.searchRead(
                'account.analytic.account',
                [],
                ['id', 'name', 'code'],
                { limit: 500, order: 'name' }
            );

            this._purchaseFilterData = {
                warehouses: warehouses,
                vendors: vendors,
                purchaseReps: purchaseReps,
                analyticAccounts: analyticAccounts
            };

            this.injectPurchaseDateFilter();
        } catch (error) {
            console.error('Error loading purchase filter data:', error);
            this.notification.add("Error loading filter options", { type: "danger" });
        }
    },

    getViewType() {
        const resModel = this.props.resModel;
        const action = this.env.config;

        if (resModel === 'purchase.order') {
            // Check if it's RFQ
            if (action.xmlId === 'purchase.purchase_rfq') {
                return 'rfq';
            }

            // Check domain for RFQ states
            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('draft') || domainStr.includes('sent')) {
                    return 'rfq';
                }
            }

            // Default to purchase order
            return 'purchase_order';
        }

        if (resModel === 'account.move') {
            return 'bill';
        }

        return 'purchase_order';
    },

    injectPurchaseDateFilter() {
        this.cleanupPurchaseFilter();

        const listTable = document.querySelector('.o_list_table');

        if (!listTable) {
            setTimeout(() => this.injectPurchaseDateFilter(), 100);
            return;
        }

        if (document.querySelector('.purchase_date_filter_wrapper_main')) {
            return;
        }

        const viewType = this.getViewType();
        const timestamp = Date.now();

        // Common field IDs
        const fromId = `purchase_date_from_${timestamp}`;
        const toId = `purchase_date_to_${timestamp}`;
        const warehouseId = `purchase_warehouse_${timestamp}`;
        const vendorId = `purchase_vendor_${timestamp}`;
        const repId = `purchase_rep_${timestamp}`;
        const analyticAccountId = `purchase_analytic_${timestamp}`;
        const orderRefId = `purchase_order_ref_${timestamp}`;
        const vendorRefId = `purchase_vendor_ref_${timestamp}`;
        const shippingRefId = `purchase_shipping_ref_${timestamp}`;
        const amountId = `purchase_amount_${timestamp}`;
        const sourceDocId = `purchase_source_doc_${timestamp}`;
        const goodsReceiptId = `purchase_goods_receipt_${timestamp}`;
        const billingStatusId = `purchase_billing_status_${timestamp}`;
        const paymentStatusId = `purchase_payment_status_${timestamp}`;

        // Set default dates (current month)
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const defaultFromDate = firstDay.toISOString().split('T')[0];
        const defaultToDate = today.toISOString().split('T')[0];

        // Build warehouse dropdown options
        let warehouseOptions = '<option value="">All Warehouses</option>';
        this._purchaseFilterData.warehouses.forEach(wh => {
            warehouseOptions += `<option value="${wh.id}">${wh.name}</option>`;
        });

        // Determine date label based on view type
        const dateLabel = viewType === 'bill' ? 'Bill Date' : 'Order Date';

        // Build filter HTML
        let filterHtml = `
            <div class="purchase_date_filter_wrapper_main">
                <div class="purchase_date_filter_container">
                    <div class="date_filter_wrapper">
                        <!-- Date Range Filter -->
                        <div class="filter_group date_group">
                            <label class="filter_label" for="${fromId}">${dateLabel}:</label>
                            <div class="date_input_group">
                                <input type="date" id="${fromId}" class="date_input" value="${defaultFromDate}" />
                                <span class="date_separator">to</span>
                                <input type="date" id="${toId}" class="date_input" value="${defaultToDate}" />
                            </div>
                        </div>

                        <!-- Warehouse Filter -->
                        <div class="filter_group">
                            <label class="filter_label" for="${warehouseId}">Warehouse:</label>
                            <select id="${warehouseId}" class="filter_select">
                                ${warehouseOptions}
                            </select>
                        </div>

                        <!-- Vendor Filter with autocomplete -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label" for="${vendorId}">Vendor:</label>
                            <div class="autocomplete_wrapper">
                                <input type="text" id="${vendorId}" class="autocomplete_input filter_input" placeholder="Vendor" autocomplete="off" />
                                <input type="hidden" id="${vendorId}_value" />
                                <div id="${vendorId}_dropdown" class="autocomplete_dropdown"></div>
                            </div>
                        </div>

                        <!-- Purchase Rep Filter with autocomplete -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label" for="${repId}">Buyer:</label>
                            <div class="autocomplete_wrapper">
                                <input type="text" id="${repId}" class="autocomplete_input filter_input" placeholder="Buyer" autocomplete="off" />
                                <input type="hidden" id="${repId}_value" />
                                <div id="${repId}_dropdown" class="autocomplete_dropdown"></div>
                            </div>
                        </div>

                        <!-- Analytic Account Filter with autocomplete -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label" for="${analyticAccountId}">Analytic Account:</label>
                            <div class="autocomplete_wrapper">
                                <input type="text" id="${analyticAccountId}" class="autocomplete_input filter_input" placeholder="Analytic Account" autocomplete="off" />
                                <input type="hidden" id="${analyticAccountId}_value" />
                                <div id="${analyticAccountId}_dropdown" class="autocomplete_dropdown"></div>
                            </div>
                        </div>

                        <!-- Reference Filter (Order/Bill Number) -->
                        <div class="filter_group">
                            <label class="filter_label" for="${orderRefId}">Reference:</label>
                            <input type="text" id="${orderRefId}" class="filter_input" placeholder="${viewType === 'bill' ? 'Bill Number' : 'Order'}" />
                        </div>

                        <!-- Vendor Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label" for="${vendorRefId}">Vendor Ref:</label>
                            <input type="text" id="${vendorRefId}" class="filter_input" placeholder="Vendor Ref" />
                        </div>

                        <!-- Shipping Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label" for="${shippingRefId}">Shipping Ref:</label>
                            <input type="text" id="${shippingRefId}" class="filter_input" placeholder="Shipping Ref" />
                        </div>
        `;

        // Add view-specific filters
        if (viewType === 'bill') {
            filterHtml += `
                        <!-- Source Document Filter (Bills only) -->
                        <div class="filter_group">
                            <label class="filter_label" for="${sourceDocId}">Source Doc:</label>
                            <input type="text" id="${sourceDocId}" class="filter_input" placeholder="Source Doc" />
                        </div>

                        <!-- Goods Receipt Filter (Bills only) -->
                        <div class="filter_group">
                            <label class="filter_label" for="${goodsReceiptId}">Goods Receipt:</label>
                            <input type="text" id="${goodsReceiptId}" class="filter_input" placeholder="Goods Receipt" />
                        </div>

                        <!-- Payment Status Filter (Bills only) -->
                        <div class="filter_group">
                            <label class="filter_label" for="${paymentStatusId}">Payment Status:</label>
                            <select id="${paymentStatusId}" class="filter_select">
                                <option value="">All Statuses</option>
                                <option value="not_paid">Not Paid</option>
                                <option value="in_payment">In Payment</option>
                                <option value="paid">Paid</option>
                                <option value="partial">Partially Paid</option>
                                <option value="reversed">Reversed</option>
                            </select>
                        </div>
            `;
        } else {
            // Billing Status Filter (Purchase Orders & RFQs only)
            filterHtml += `
                        <div class="filter_group">
                            <label class="filter_label" for="${billingStatusId}">Billing Status:</label>
                            <select id="${billingStatusId}" class="filter_select">
                                <option value="">All Statuses</option>
                                <option value="no">Nothing to Bill</option>
                                <option value="to invoice">To Bill</option>
                                <option value="invoiced">Fully Billed</option>
                            </select>
                        </div>
            `;
        }

        // Amount Filter
        filterHtml += `
                        <div class="filter_group amount_group">
                            <label class="filter_label" for="${amountId}">Amount:</label>
                            <div class="amount_input_group">
                                <input type="number" id="${amountId}" class="amount_input" placeholder="Amount" step="0.01" />
                            </div>
                        </div>

                        <!-- Apply and Clear buttons -->
                        <div class="filter_actions">
                            <button id="apply_purchase_filter_${timestamp}" class="btn btn-primary apply_filter_btn">
                                Apply
                            </button>
                            <button id="clear_purchase_filter_${timestamp}" class="btn btn-secondary clear_filter_btn">
                                Clear
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert filter before the table
        listTable.insertAdjacentHTML('beforebegin', filterHtml);

        // Get filter elements
        const dateFromInput = document.getElementById(fromId);
        const dateToInput = document.getElementById(toId);
        const warehouseSelect = document.getElementById(warehouseId);
        const vendorInput = document.getElementById(vendorId);
        const vendorValue = document.getElementById(`${vendorId}_value`);
        const vendorDropdown = document.getElementById(`${vendorId}_dropdown`);
        const repInput = document.getElementById(repId);
        const repValue = document.getElementById(`${repId}_value`);
        const repDropdown = document.getElementById(`${repId}_dropdown`);
        const analyticInput = document.getElementById(analyticAccountId);
        const analyticValue = document.getElementById(`${analyticAccountId}_value`);
        const analyticDropdown = document.getElementById(`${analyticAccountId}_dropdown`);
        const orderRefInput = document.getElementById(orderRefId);
        const vendorRefInput = document.getElementById(vendorRefId);
        const shippingRefInput = document.getElementById(shippingRefId);
        const amountInput = document.getElementById(amountId);
        const sourceDocInput = document.getElementById(sourceDocId);
        const goodsReceiptInput = document.getElementById(goodsReceiptId);
        const billingStatusSelect = document.getElementById(billingStatusId);
        const paymentStatusSelect = document.getElementById(paymentStatusId);
        const applyBtn = document.getElementById(`apply_purchase_filter_${timestamp}`);
        const clearBtn = document.getElementById(`clear_purchase_filter_${timestamp}`);

        this._purchaseFilterElement = document.querySelector('.purchase_date_filter_wrapper_main');

        // Autocomplete functionality for Vendor
        const setupVendorAutocomplete = () => {
            let vendorList = this._purchaseFilterData.vendors;

            vendorInput.addEventListener('input', () => {
                const searchValue = vendorInput.value.toLowerCase();

                if (searchValue.length < 1) {
                    vendorDropdown.classList.remove('show');
                    return;
                }

                const filtered = vendorList.filter(v =>
                    v.name.toLowerCase().includes(searchValue)
                ).slice(0, 50);

                if (filtered.length === 0) {
                    vendorDropdown.innerHTML = '<div class="autocomplete_item no_results">No vendors found</div>';
                    vendorDropdown.classList.add('show');
                    return;
                }

                vendorDropdown.innerHTML = filtered.map(v =>
                    `<div class="autocomplete_item" data-id="${v.id}">${v.name}</div>`
                ).join('');
                vendorDropdown.classList.add('show');
            });

            vendorDropdown.addEventListener('click', (e) => {
                if (e.target.classList.contains('autocomplete_item') && !e.target.classList.contains('no_results')) {
                    const id = e.target.getAttribute('data-id');
                    const name = e.target.textContent;
                    vendorInput.value = name;
                    vendorValue.value = id;
                    vendorDropdown.classList.remove('show');
                }
            });

            vendorInput.addEventListener('blur', () => {
                setTimeout(() => vendorDropdown.classList.remove('show'), 200);
            });

            vendorInput.addEventListener('focus', () => {
                if (vendorInput.value.length >= 1) {
                    vendorInput.dispatchEvent(new Event('input'));
                }
            });
        };

        // Autocomplete functionality for Purchase Rep
        const setupRepAutocomplete = () => {
            let repList = this._purchaseFilterData.purchaseReps;

            repInput.addEventListener('input', () => {
                const searchValue = repInput.value.toLowerCase();

                if (searchValue.length < 1) {
                    repDropdown.classList.remove('show');
                    return;
                }

                const filtered = repList.filter(r =>
                    r.name.toLowerCase().includes(searchValue)
                ).slice(0, 50);

                if (filtered.length === 0) {
                    repDropdown.innerHTML = '<div class="autocomplete_item no_results">No users found</div>';
                    repDropdown.classList.add('show');
                    return;
                }

                repDropdown.innerHTML = filtered.map(r =>
                    `<div class="autocomplete_item" data-id="${r.id}">${r.name}</div>`
                ).join('');
                repDropdown.classList.add('show');
            });

            repDropdown.addEventListener('click', (e) => {
                if (e.target.classList.contains('autocomplete_item') && !e.target.classList.contains('no_results')) {
                    const id = e.target.getAttribute('data-id');
                    const name = e.target.textContent;
                    repInput.value = name;
                    repValue.value = id;
                    repDropdown.classList.remove('show');
                }
            });

            repInput.addEventListener('blur', () => {
                setTimeout(() => repDropdown.classList.remove('show'), 200);
            });

            repInput.addEventListener('focus', () => {
                if (repInput.value.length >= 1) {
                    repInput.dispatchEvent(new Event('input'));
                }
            });
        };

        // Autocomplete functionality for Analytic Account
        const setupAnalyticAutocomplete = () => {
            let analyticList = this._purchaseFilterData.analyticAccounts;

            analyticInput.addEventListener('input', () => {
                const searchValue = analyticInput.value.toLowerCase();

                if (searchValue.length < 1) {
                    analyticDropdown.classList.remove('show');
                    return;
                }

                const filtered = analyticList.filter(a =>
                    a.name.toLowerCase().includes(searchValue) ||
                    (a.code && a.code.toLowerCase().includes(searchValue))
                ).slice(0, 50);

                if (filtered.length === 0) {
                    analyticDropdown.innerHTML = '<div class="autocomplete_item no_results">No analytic accounts found</div>';
                    analyticDropdown.classList.add('show');
                    return;
                }

                analyticDropdown.innerHTML = filtered.map(a => {
                    const displayName = a.code ? `${a.code} - ${a.name}` : a.name;
                    return `<div class="autocomplete_item" data-id="${a.id}">${displayName}</div>`;
                }).join('');
                analyticDropdown.classList.add('show');
            });

            analyticDropdown.addEventListener('click', (e) => {
                if (e.target.classList.contains('autocomplete_item') && !e.target.classList.contains('no_results')) {
                    const id = e.target.getAttribute('data-id');
                    const name = e.target.textContent;
                    console.log('Analytic selected - ID:', id, 'Name:', name);
                    analyticInput.value = name;
                    analyticValue.value = id;
                    console.log('After setting - analyticValue.value:', analyticValue.value);
                    analyticDropdown.classList.remove('show');
                }
            });

            analyticInput.addEventListener('blur', () => {
                setTimeout(() => analyticDropdown.classList.remove('show'), 200);
            });

            analyticInput.addEventListener('focus', () => {
                if (analyticInput.value.length >= 1) {
                    analyticInput.dispatchEvent(new Event('input'));
                }
            });
        };

        // Initialize autocomplete
        setupVendorAutocomplete();
        setupRepAutocomplete();
        setupAnalyticAutocomplete();

        // Apply filter function
        const applyFilter = () => {
            try {
                // Debug: Check all elements exist
                console.log('=== Filter Elements Debug ===');
                console.log('dateFromInput:', dateFromInput ? 'EXISTS' : 'NULL');
                console.log('dateToInput:', dateToInput ? 'EXISTS' : 'NULL');
                console.log('analyticInput:', analyticInput ? 'EXISTS' : 'NULL');
                console.log('analyticValue:', analyticValue ? 'EXISTS' : 'NULL');
                console.log('analyticValue ID:', analyticValue ? analyticValue.id : 'NULL');
                console.log('============================');

                const dateFrom = dateFromInput.value;
                const dateTo = dateToInput.value;

                if (!dateFrom || !dateTo) {
                    this.notification.add("Please select both From and To dates", { type: "warning" });
                    return;
                }

                if (dateFrom > dateTo) {
                    this.notification.add("From date must be before To date", { type: "warning" });
                    return;
                }

                let domain = [];
                let context = {};
                let resModel = '';
                let actionName = '';

                // Build domain based on view type
                if (viewType === 'purchase_order') {
                    domain = [
                        ['date_order', '>=', dateFrom + ' 00:00:00'],
                        ['date_order', '<=', dateTo + ' 23:59:59'],
                        ['state', 'in', ['purchase', 'done']]
                    ];
                    resModel = 'purchase.order';
                    actionName = 'Purchase Orders';
                } else if (viewType === 'rfq') {
                    domain = [
                        ['date_order', '>=', dateFrom + ' 00:00:00'],
                        ['date_order', '<=', dateTo + ' 23:59:59'],
                        ['state', 'in', ['draft', 'sent', 'to approve']]
                    ];
                    resModel = 'purchase.order';
                    actionName = 'Request for Quotations';
                } else if (viewType === 'bill') {
                    domain = [
                        ['invoice_date', '>=', dateFrom],
                        ['invoice_date', '<=', dateTo],
                        ['move_type', '=', 'in_invoice'],
                        ['state', '!=', 'cancel']
                    ];
                    resModel = 'account.move';
                    actionName = 'Vendor Bills';
                    context = {
                        'default_move_type': 'in_invoice',
                    };
                }

                // Common filters for all view types

                // Vendor filter
                if (vendorValue.value) {
                    domain.push(['partner_id', '=', parseInt(vendorValue.value)]);
                }

                // Purchase rep/buyer filter
                if (repValue.value) {
                    if (viewType === 'bill') {
                        // Use buyer_id for bills (if available) or invoice_user_id
                        domain.push('|');
                        domain.push(['invoice_user_id', '=', parseInt(repValue.value)]);
                        domain.push(['user_id', '=', parseInt(repValue.value)]);
                    } else {
                        domain.push(['user_id', '=', parseInt(repValue.value)]);
                    }
                }

                // Analytic Account filter - Using the correct field path
                console.log('Analytic Input Value:', analyticInput ? analyticInput.value : 'NULL');
                console.log('Analytic Hidden Value:', analyticValue ? analyticValue.value : 'NULL');

                if (analyticValue && analyticValue.value && analyticValue.value.trim() !== '') {
                    const analyticId = parseInt(analyticValue.value);
                    console.log('Applying analytic filter with ID:', analyticId);

                    if (viewType === 'bill') {
                        // For bills in Odoo 19, analytic_distribution is stored as JSON
                        // Format: {"account_id": percentage}
                        // We search for the ID in the JSON string
                        domain.push('|');
                        domain.push('|');
                        domain.push(['line_ids.analytic_distribution', 'ilike', `"${analyticId}"`]);
                        domain.push(['invoice_line_ids.analytic_distribution', 'ilike', `"${analyticId}"`]);
                        // Also try the old field name if it exists
                        domain.push(['line_ids.analytic_account_id', '=', analyticId]);
                    } else {
                        // For purchase orders
                        domain.push('|');
                        domain.push(['order_line.analytic_distribution', 'ilike', `"${analyticId}"`]);
                        // Also try the old field name if it exists
                        domain.push(['order_line.account_analytic_id', '=', analyticId]);
                    }
                } else {
                    console.log('Analytic filter NOT applied - no value selected');
                }

                // Reference filter (Order/Bill number)
                if (orderRefInput.value.trim()) {
                    domain.push(['name', 'ilike', orderRefInput.value.trim()]);
                }

                // Vendor reference filter
                if (vendorRefInput.value.trim()) {
                    if (viewType === 'bill') {
                        domain.push(['ref', 'ilike', vendorRefInput.value.trim()]);
                    } else {
                        domain.push(['partner_ref', 'ilike', vendorRefInput.value.trim()]);
                    }
                }

                // Amount filter
                if (amountInput.value) {
                    const exactAmount = parseFloat(amountInput.value);
                    domain.push(['amount_total', '=', exactAmount]);
                }

                // View-specific filters
                if (viewType === 'purchase_order' || viewType === 'rfq') {
                    // Warehouse filter
                    if (warehouseSelect.value) {
                        domain.push(['picking_type_id.warehouse_id', '=', parseInt(warehouseSelect.value)]);
                    }

                    // Shipping reference filter
                    if (shippingRefInput.value.trim()) {
                        domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
                    }

                    // Billing status filter
                    if (billingStatusSelect && billingStatusSelect.value) {
                        domain.push(['invoice_status', '=', billingStatusSelect.value]);
                    }
                } else if (viewType === 'bill') {
                    // Warehouse filter for bills
                    if (warehouseSelect.value) {
                        domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
                    }

                    // Source document filter
                    if (sourceDocInput && sourceDocInput.value.trim()) {
                        domain.push(['invoice_origin', 'ilike', sourceDocInput.value.trim()]);
                    }

                    // Shipping reference filter (awb_number field)
                    if (shippingRefInput.value.trim()) {
                        domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
                    }

                    // Goods Receipt filter (goods_receipt_number field)
                    if (goodsReceiptInput && goodsReceiptInput.value.trim()) {
                        domain.push(['goods_receipt_number', 'ilike', goodsReceiptInput.value.trim()]);
                    }

                    // Payment status filter
                    if (paymentStatusSelect && paymentStatusSelect.value) {
                        domain.push(['payment_state', '=', paymentStatusSelect.value]);
                    }
                }

                console.log('Applying domain:', JSON.stringify(domain, null, 2));

                // Check if model and controller still exist before reloading
                if (this.model && this.model.load) {
                    this.model.load({ domain: domain, context: context }).catch((error) => {
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
            dateFromInput, dateToInput, warehouseSelect, vendorInput, repInput, analyticInput,
            orderRefInput, vendorRefInput, shippingRefInput, amountInput
        ];

        // Add bill-specific inputs if they exist
        if (sourceDocInput) allInputs.push(sourceDocInput);
        if (goodsReceiptInput) allInputs.push(goodsReceiptInput);
        if (billingStatusSelect) allInputs.push(billingStatusSelect);
        if (paymentStatusSelect) allInputs.push(paymentStatusSelect);

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
                warehouseSelect.value = '';
                vendorInput.value = '';
                vendorValue.value = '';
                repInput.value = '';
                repValue.value = '';
                analyticInput.value = '';
                analyticValue.value = '';
                orderRefInput.value = '';
                vendorRefInput.value = '';
                shippingRefInput.value = '';
                amountInput.value = '';

                if (sourceDocInput) sourceDocInput.value = '';
                if (goodsReceiptInput) goodsReceiptInput.value = '';
                if (billingStatusSelect) billingStatusSelect.value = '';
                if (paymentStatusSelect) paymentStatusSelect.value = '';

                let domain = [];
                let context = {};

                if (viewType === 'purchase_order') {
                    domain = [['state', 'in', ['purchase', 'done']]];
                } else if (viewType === 'rfq') {
                    domain = [['state', 'in', ['draft', 'sent', 'to approve']]];
                } else if (viewType === 'bill') {
                    domain = [['move_type', '=', 'in_invoice']];
                    context = {
                        'default_move_type': 'in_invoice',
                    };
                }

                // Check if model and controller still exist before reloading
                if (this.model && this.model.load) {
                    this.model.load({ domain: domain, context: context }).catch((error) => {
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