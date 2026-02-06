/** @odoo-module **/

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
            analyticAccounts: []  // Added analytic accounts
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
            // Load warehouses, vendors, purchase reps, and analytic accounts
            const [warehouses, vendors, purchaseReps, analyticAccounts] = await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name'], { limit: 100 }),
                this.orm.searchRead('res.partner', [['supplier_rank', '>', 0]], ['id', 'name'],
                    { limit: 500, order: 'name' }),
                this.orm.searchRead('res.users', [], ['id', 'name'], { limit: 100, order: 'name' }),
                this.orm.searchRead('account.analytic.account', [], ['id', 'name', 'code'],
                    { limit: 500, order: 'name' })
            ]);

            this._purchaseFilterData = {
                warehouses: warehouses || [],
                vendors: vendors || [],
                purchaseReps: purchaseReps || [],
                analyticAccounts: analyticAccounts || []
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

        // Check RFQ
        if (resModel === 'purchase.order') {
            if (action.xmlId === 'purchase.purchase_rfq') {
                return 'rfq';
            }

            if (action.displayName || action.name) {
                const actionName = (action.displayName || action.name).toLowerCase();
                if (actionName.includes('rfq') || actionName.includes('request for quotation')) {
                    return 'rfq';
                }
            }

            if (this.props.domain) {
                const domainStr = JSON.stringify(this.props.domain);
                if (domainStr.includes('draft') || domainStr.includes('sent')) {
                    return 'rfq';
                }
            }
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
        const analyticId = `purchase_analytic_${timestamp}`;  // Added analytic account ID
        const orderRefId = `purchase_order_ref_${timestamp}`;
        const vendorRefId = `purchase_vendor_ref_${timestamp}`;
        const shippingRefId = `purchase_shipping_ref_${timestamp}`;
        const amountId = `purchase_amount_${timestamp}`;
        const sourceDocId = `purchase_source_doc_${timestamp}`;
        const goodsReceiptId = `purchase_goods_receipt_${timestamp}`;
        const billingStatusId = `purchase_billing_status_${timestamp}`;
        const paymentStatusId = `purchase_payment_status_${timestamp}`;
        const applyId = `purchase_apply_${timestamp}`;
        const clearId = `purchase_clear_${timestamp}`;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        // Build warehouse options
        const warehouseOptions = this._purchaseFilterData.warehouses
            .map(w => `<option value="${w.id}">${w.name}</option>`)
            .join('');

        let filterHTML = '';

        // Generate filter HTML based on view type
        if (viewType === 'purchase_order' || viewType === 'rfq') {
            // Purchase Order and RFQ filters
            filterHTML = `
                <div class="purchase_date_filter_container">
                    <div class="date_filter_wrapper">
                        <!-- Date Range Filter -->
                        <div class="filter_group date_group">
                            <label class="filter_label">Order Date:</label>
                            <div class="date_input_group">
                                <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
                                <span class="date_separator">→</span>
                                <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
                            </div>
                        </div>

                        <!-- Order Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Order Ref:</label>
                            <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="${viewType === 'rfq' ? 'RFQ...' : 'PO...'}" />
                        </div>

                        <!-- Vendor Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Vendor:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${vendorId}_input"
                                    placeholder="Vendor"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${vendorId}_value" />
                                <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Vendor Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Vendor Ref:</label>
                            <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
                        </div>

                        <!-- Warehouse Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Warehouse:</label>
                            <select class="form-select filter_select" id="${warehouseId}">
                                <option value="">Warehouse</option>
                                ${warehouseOptions}
                            </select>
                        </div>

                        <!-- Shipping Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Shipping Ref:</label>
                            <input type="text" class="form-control filter_input" id="${shippingRefId}" placeholder="AWB..." />
                        </div>

                        <!-- Total Amount Filter -->
                        <div class="filter_group amount_group">
                            <label class="filter_label">Amount:</label>
                            <input type="number" class="form-control amount_input" id="${amountId}" placeholder="Total Amount" step="0.01" />
                        </div>

                        <!-- Purchase Rep Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Purchase Rep:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${repId}_input"
                                    placeholder="Purchase Rep"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${repId}_value" />
                                <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Analytic Account Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Analytic:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${analyticId}_input"
                                    placeholder="Analytic Account"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${analyticId}_value" />
                                <div class="autocomplete_dropdown" id="${analyticId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Billing Status Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Billing Status:</label>
                            <select class="form-select filter_select" id="${billingStatusId}">
                                <option value="">Billing Status</option>
                                <option value="no">Nothing to Bill</option>
                                <option value="to invoice">To Invoice</option>
                                <option value="invoiced">Fully Invoiced</option>
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
        } else if (viewType === 'bill') {
            // Vendor Bill filters
            filterHTML = `
                <div class="purchase_date_filter_container">
                    <div class="date_filter_wrapper">
                        <!-- Date Range Filter -->
                        <div class="filter_group date_group">
                            <label class="filter_label">Bill Date:</label>
                            <div class="date_input_group">
                                <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
                                <span class="date_separator">→</span>
                                <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
                            </div>
                        </div>

                        <!-- Bill Number Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Bill Number:</label>
                            <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="BILL..." />
                        </div>

                        <!-- Vendor Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Vendor:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${vendorId}_input"
                                    placeholder="Vendor"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${vendorId}_value" />
                                <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Warehouse Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Warehouse:</label>
                            <select class="form-select filter_select" id="${warehouseId}">
                                <option value="">Warehouse</option>
                                ${warehouseOptions}
                            </select>
                        </div>

                        <!-- Source Document Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Source Doc:</label>
                            <input type="text" class="form-control filter_input" id="${sourceDocId}" placeholder="Source Doc..." />
                        </div>

                        <!-- Vendor Reference Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Vendor Ref:</label>
                            <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
                        </div>

                        <!-- Total Amount Filter -->
                        <div class="filter_group amount_group">
                            <label class="filter_label">Amount:</label>
                            <input type="number" class="form-control amount_input" id="${amountId}" placeholder="Total Amount" step="0.01" />
                        </div>

                        <!-- Buyer Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Buyer:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${repId}_input"
                                    placeholder="Buyer"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${repId}_value" />
                                <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Analytic Account Filter (Searchable) -->
                        <div class="filter_group autocomplete_group">
                            <label class="filter_label">Analytic:</label>
                            <div class="autocomplete_wrapper">
                                <input
                                    type="text"
                                    class="form-control autocomplete_input"
                                    id="${analyticId}_input"
                                    placeholder="Analytic Account"
                                    autocomplete="off"
                                />
                                <input type="hidden" id="${analyticId}_value" />
                                <div class="autocomplete_dropdown" id="${analyticId}_dropdown"></div>
                            </div>
                        </div>

                        <!-- Payment Status Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Payment Status:</label>
                            <select class="form-select filter_select" id="${paymentStatusId}">
                                <option value="">Payment Status</option>
                                <option value="not_paid">Not Paid</option>
                                <option value="in_payment">In Payment</option>
                                <option value="paid">Paid</option>
                                <option value="partial">Partially Paid</option>
                                <option value="reversed">Reversed</option>
                            </select>
                        </div>

                        <!-- Goods Receipt Filter -->
                        <div class="filter_group">
                            <label class="filter_label">Goods Receipt:</label>
                            <input type="text" class="form-control filter_input" id="${goodsReceiptId}" placeholder="Receipt..." />
                        </div>

                        <!-- Action Buttons -->
                        <div class="filter_actions">
                            <button class="btn btn-primary apply_filter_btn" id="${applyId}">Apply</button>
                            <button class="btn btn-secondary clear_filter_btn" id="${clearId}">Clear</button>
                        </div>
                    </div>
                </div>
            `;
        }

        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = 'purchase_date_filter_wrapper_main';
        wrapperDiv.innerHTML = filterHTML;
        listTable.parentNode.insertBefore(wrapperDiv, listTable);

        this._purchaseFilterElement = wrapperDiv;

        this.attachPurchaseFilterListeners(fromId, toId, warehouseId, vendorId, repId, analyticId,
            orderRefId, vendorRefId, shippingRefId, amountId, sourceDocId, goodsReceiptId,
            billingStatusId, paymentStatusId, applyId, clearId, viewType);
    },

    attachPurchaseFilterListeners(fromId, toId, warehouseId, vendorId, repId, analyticId,
        orderRefId, vendorRefId, shippingRefId, amountId, sourceDocId, goodsReceiptId,
        billingStatusId, paymentStatusId, applyId, clearId, viewType) {

        // Define model type flags at the beginning
        const isPurchaseOrder = viewType === 'purchase_order' || viewType === 'rfq';
        const isBill = viewType === 'bill';
        const resModel = this.props.resModel;

        const fromInput = document.getElementById(fromId);
        const toInput = document.getElementById(toId);
        const warehouseSelect = document.getElementById(warehouseId);
        const vendorInput = document.getElementById(`${vendorId}_input`);
        const vendorValue = document.getElementById(`${vendorId}_value`);
        const vendorDropdown = document.getElementById(`${vendorId}_dropdown`);
        const repInput = document.getElementById(`${repId}_input`);
        const repValue = document.getElementById(`${repId}_value`);
        const repDropdown = document.getElementById(`${repId}_dropdown`);
        const analyticInput = document.getElementById(`${analyticId}_input`);
        const analyticValue = document.getElementById(`${analyticId}_value`);
        const analyticDropdown = document.getElementById(`${analyticId}_dropdown`);
        const orderRefInput = document.getElementById(orderRefId);
        const vendorRefInput = document.getElementById(vendorRefId);
        const shippingRefInput = document.getElementById(shippingRefId);
        const amountInput = document.getElementById(amountId);
        const sourceDocInput = document.getElementById(sourceDocId);
        const goodsReceiptInput = document.getElementById(goodsReceiptId);
        const billingStatusSelect = document.getElementById(billingStatusId);
        const paymentStatusSelect = document.getElementById(paymentStatusId);
        const applyBtn = document.getElementById(applyId);
        const clearBtn = document.getElementById(clearId);

        // Vendor autocomplete
        if (vendorInput && vendorDropdown) {
            vendorInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showVendorDropdown(vendorDropdown, searchTerm);
                } else {
                    this.showVendorDropdown(vendorDropdown, '');
                }
            });

            vendorInput.addEventListener('focus', () => {
                const searchTerm = vendorInput.value.trim();
                this.showVendorDropdown(vendorDropdown, searchTerm || '');
            });

            vendorInput.addEventListener('click', () => {
                const searchTerm = vendorInput.value.trim();
                this.showVendorDropdown(vendorDropdown, searchTerm || '');
            });

            vendorDropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    vendorValue.value = item.dataset.id;
                    vendorInput.value = item.textContent;
                    vendorDropdown.classList.remove('show');
                }
            });

            document.addEventListener('click', (e) => {
                if (!vendorInput.contains(e.target) && !vendorDropdown.contains(e.target)) {
                    vendorDropdown.classList.remove('show');
                }
            });
        }

        // Purchase rep autocomplete
        if (repInput && repDropdown) {
            repInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showPurchaseRepDropdown(repDropdown, searchTerm);
                } else {
                    this.showPurchaseRepDropdown(repDropdown, '');
                }
            });

            repInput.addEventListener('focus', () => {
                const searchTerm = repInput.value.trim();
                this.showPurchaseRepDropdown(repDropdown, searchTerm || '');
            });

            repInput.addEventListener('click', () => {
                const searchTerm = repInput.value.trim();
                this.showPurchaseRepDropdown(repDropdown, searchTerm || '');
            });

            repDropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    repValue.value = item.dataset.id;
                    repInput.value = item.textContent;
                    repDropdown.classList.remove('show');
                }
            });

            document.addEventListener('click', (e) => {
                if (!repInput.contains(e.target) && !repDropdown.contains(e.target)) {
                    repDropdown.classList.remove('show');
                }
            });
        }

        // Analytic account autocomplete
        if (analyticInput && analyticDropdown) {
            analyticInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    this.showAnalyticDropdown(analyticDropdown, searchTerm);
                } else {
                    this.showAnalyticDropdown(analyticDropdown, '');
                }
            });

            analyticInput.addEventListener('focus', () => {
                const searchTerm = analyticInput.value.trim();
                this.showAnalyticDropdown(analyticDropdown, searchTerm || '');
            });

            analyticInput.addEventListener('click', () => {
                const searchTerm = analyticInput.value.trim();
                this.showAnalyticDropdown(analyticDropdown, searchTerm || '');
            });

            analyticDropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.autocomplete_item');
                if (item && !item.classList.contains('no_results')) {
                    analyticValue.value = item.dataset.id;
                    analyticInput.value = item.textContent;
                    analyticDropdown.classList.remove('show');
                }
            });

            document.addEventListener('click', (e) => {
                if (!analyticInput.contains(e.target) && !analyticDropdown.contains(e.target)) {
                    analyticDropdown.classList.remove('show');
                }
            });
        }

        // Apply filters
        const applyFilters = async () => {
            const dateFrom = fromInput?.value;
            const dateTo = toInput?.value;
            const warehouse = warehouseSelect?.value;
            const vendor = vendorValue?.value;
            const rep = repValue?.value;
            const analytic = analyticValue?.value;
            const orderRef = orderRefInput?.value.trim();
            const vendorRef = vendorRefInput?.value.trim();
            const shippingRef = shippingRefInput?.value.trim();
            const amount = amountInput?.value.trim();
            const sourceDoc = sourceDocInput?.value.trim();
            const goodsReceipt = goodsReceiptInput?.value.trim();
            const billingStatus = billingStatusSelect?.value;
            const paymentStatus = paymentStatusSelect?.value;

            let domain = [];
            if (isBill) {
                domain.push(['move_type', '=', 'in_invoice']);
            }

            // Date range filter
            if (dateFrom || dateTo) {
                const dateField = isPurchaseOrder ? 'date_order' : 'invoice_date';
                if (dateFrom && dateTo) {
                    domain.push([dateField, '>=', dateFrom + ' 00:00:00']);
                    domain.push([dateField, '<=', dateTo + ' 23:59:59']);
                } else if (dateFrom) {
                    domain.push([dateField, '>=', dateFrom + ' 00:00:00']);
                } else if (dateTo) {
                    domain.push([dateField, '<=', dateTo + ' 23:59:59']);
                }
            }

            // Vendor filter
            if (vendor) {
                domain.push(['partner_id', '=', parseInt(vendor)]);
            }

            // Purchase rep filter
            if (rep) {
                domain.push(['user_id', '=', parseInt(rep)]);
            }

            // Analytic account filter
            if (analytic) {
                if (isPurchaseOrder) {
                    // For purchase orders, check order lines
                    try {
                        const poLines = await this.orm.searchRead(
                            'purchase.order.line',
                            [['analytic_distribution', '!=', false]],
                            ['order_id', 'analytic_distribution'],
                            { limit: 5000 }
                        );

                        const matchingPOIds = [];
                        for (const line of poLines) {
                            if (line.analytic_distribution) {
                                const distribution = typeof line.analytic_distribution === 'string'
                                    ? JSON.parse(line.analytic_distribution)
                                    : line.analytic_distribution;

                                if (distribution[analytic.toString()]) {
                                    matchingPOIds.push(line.order_id[0]);
                                }
                            }
                        }

                        if (matchingPOIds.length > 0) {
                            const uniquePOIds = [...new Set(matchingPOIds)];
                            domain.push(['id', 'in', uniquePOIds]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Analytic account filter error:', error);
                        this.notification.add("Error applying analytic account filter", { type: "danger" });
                        return;
                    }
                } else {
                    // For vendor bills, check invoice lines
                    try {
                        const billLines = await this.orm.searchRead(
                            'account.move.line',
                            [
                                ['move_id.move_type', '=', 'in_invoice'],
                                ['analytic_distribution', '!=', false]
                            ],
                            ['move_id', 'analytic_distribution'],
                            { limit: 5000 }
                        );

                        const matchingBillIds = [];
                        for (const line of billLines) {
                            if (line.analytic_distribution) {
                                const distribution = typeof line.analytic_distribution === 'string'
                                    ? JSON.parse(line.analytic_distribution)
                                    : line.analytic_distribution;

                                if (distribution[analytic.toString()]) {
                                    matchingBillIds.push(line.move_id[0]);
                                }
                            }
                        }

                        if (matchingBillIds.length > 0) {
                            const uniqueBillIds = [...new Set(matchingBillIds)];
                            domain.push(['id', 'in', uniqueBillIds]);
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

            // Order/Bill reference filter
            if (orderRef) {
                domain.push(['name', 'ilike', orderRef]);
            }

            // Vendor reference filter
            if (vendorRef) {
                domain.push(['partner_ref', 'ilike', vendorRef]);
            }

            // Amount filter
            if (amount) {
                const amountValue = parseFloat(amount);
                if (!isNaN(amountValue)) {
                    domain.push(['amount_total', '=', amountValue]);
                }
            }

            // Warehouse filter
            if (warehouse) {
                if (isPurchaseOrder) {
                    domain.push(['picking_type_id.warehouse_id', '=', parseInt(warehouse)]);
                } else {
                    // For bills, find purchase orders with this warehouse and their related bills
                    try {
                        const pos = await this.orm.searchRead(
                            'purchase.order',
                            [['picking_type_id.warehouse_id', '=', parseInt(warehouse)]],
                            ['name'],
                            { limit: 500 }
                        );

                        if (pos.length > 0) {
                            const poNames = pos.map(po => po.name);
                            domain.push(['invoice_origin', 'in', poNames]);
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

            // Source document filter (for bills)
            if (sourceDoc && isBill) {
                domain.push(['invoice_origin', 'ilike', sourceDoc]);
            }

            // Goods receipt filter (for bills)
            if (goodsReceipt && isBill) {
                try {
                    const pickings = await this.orm.searchRead(
                        'stock.picking',
                        [['name', 'ilike', goodsReceipt]],
                        ['purchase_id'],
                        { limit: 500 }
                    );

                    const poIds = [...new Set(
                        pickings
                            .filter(p => p.purchase_id)
                            .map(p => p.purchase_id[0])
                    )];

                    if (poIds.length > 0) {
                        const pos = await this.orm.searchRead(
                            'purchase.order',
                            [['id', 'in', poIds]],
                            ['name'],
                            { limit: 200 }
                        );
                        const poNames = pos.map(po => po.name);
                        domain.push(['invoice_origin', 'in', poNames]);
                    } else {
                        domain.push(['id', '=', -1]);
                    }
                } catch (error) {
                    console.error('Goods receipt filter error:', error);
                    this.notification.add("Error applying goods receipt filter", { type: "danger" });
                    return;
                }
            }

            // Shipping reference filter (AWB)
            if (shippingRef) {
                if (isPurchaseOrder) {
                    try {
                        const pickings = await this.orm.searchRead(
                            'stock.picking',
                            [
                                ['carrier_tracking_ref', 'ilike', shippingRef],
                                ['purchase_id', '!=', false]
                            ],
                            ['purchase_id'],
                            { limit: 500 }
                        );

                        const poIds = [...new Set(
                            pickings
                                .filter(p => p.purchase_id)
                                .map(p => p.purchase_id[0])
                        )];

                        if (poIds.length > 0) {
                            domain.push(['id', 'in', poIds]);
                        } else {
                            domain.push(['id', '=', -1]);
                        }
                    } catch (error) {
                        console.error('Shipping ref filter error:', error);
                        this.notification.add("Error applying shipping filter", { type: "danger" });
                        return;
                    }
                }
            }

            // Billing status filter (for PO)
            if (billingStatus && isPurchaseOrder) {
                domain.push(['invoice_status', '=', billingStatus]);
            }

            // Payment status filter (for bills)
            if (paymentStatus && isBill) {
                domain.push(['payment_state', '=', paymentStatus]);
            }

            const actionConfig = this._getActionConfig();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isPurchaseOrder ? 'Purchase Orders' : 'Vendor Bills',
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

            if (fromInput) fromInput.value = firstDay.toISOString().split('T')[0];
            if (toInput) toInput.value = today.toISOString().split('T')[0];
            if (warehouseSelect) warehouseSelect.value = '';
            if (vendorInput) vendorInput.value = '';
            if (vendorValue) vendorValue.value = '';
            if (repInput) repInput.value = '';
            if (repValue) repValue.value = '';
            if (analyticInput) analyticInput.value = '';
            if (analyticValue) analyticValue.value = '';
            if (orderRefInput) orderRefInput.value = '';
            if (vendorRefInput) vendorRefInput.value = '';
            if (shippingRefInput) shippingRefInput.value = '';
            if (amountInput) amountInput.value = '';
            if (sourceDocInput) sourceDocInput.value = '';
            if (goodsReceiptInput) goodsReceiptInput.value = '';
            if (billingStatusSelect) billingStatusSelect.value = '';
            if (paymentStatusSelect) paymentStatusSelect.value = '';

            let domain = [];
            if (isBill) {
                domain = [['move_type', '=', 'in_invoice']];
            }

            const actionConfig = this._getActionConfig();

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: isPurchaseOrder ? 'Purchase Orders' : 'Vendor Bills',
                res_model: resModel,
                views: actionConfig.views,
                view_id: actionConfig.viewId,
                search_view_id: actionConfig.searchViewId,
                domain: domain,
                context: actionConfig.context,
                target: 'current',
            });

            this.notification.add("Filters cleared", { type: "info" });
        };

        applyBtn?.addEventListener('click', applyFilters);
        clearBtn?.addEventListener('click', clearFilters);

        // Enter key to apply
        [fromInput, toInput, orderRefInput, vendorRefInput, shippingRefInput,
         amountInput, sourceDocInput, goodsReceiptInput].forEach(el => {
            if (el) {
                el.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyFilters();
                    }
                });
            }
        });

        // Escape to clear
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearFilters();
            }
        });
    },

    _getActionConfig() {
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

    _getCurrentActionViews() {
        try {
            const action = this.actionService?.currentController?.action;
            if (action && action.views && action.views.length > 0) {
                return action.views;
            }
        } catch (e) {
            console.debug('Could not get current action views:', e);
        }

        if (this.props.views && this.props.views.length > 0) {
            return this.props.views;
        }

        return [[false, 'list'], [false, 'form']];
    },

    _getCurrentActionContext() {
        try {
            const action = this.actionService?.currentController?.action;
            if (action && action.context) {
                return { ...action.context };
            }
        } catch (e) {
            console.debug('Could not get current action context:', e);
        }

        return { ...(this.props.context || {}) };
    },

    showVendorDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.vendors;
        } else {
            filtered = this._purchaseFilterData.vendors.filter(v =>
                v.name ? v.name.toLowerCase().includes(lowerSearch) : false
            );
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No vendors found</div>';
        } else {
            dropdown.innerHTML = filtered.map(v =>
                `<div class="autocomplete_item" data-id="${v.id}">${v.name || ''}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },

    showPurchaseRepDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.purchaseReps;
        } else {
            filtered = this._purchaseFilterData.purchaseReps.filter(r =>
                r.name ? r.name.toLowerCase().includes(lowerSearch) : false
            );
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No users found</div>';
        } else {
            dropdown.innerHTML = filtered.map(r =>
                `<div class="autocomplete_item" data-id="${r.id}">${r.name || ''}</div>`
            ).join('');
        }

        dropdown.classList.add('show');
    },

    showAnalyticDropdown(dropdown, searchTerm) {
        // Safety check for searchTerm
        searchTerm = searchTerm || '';
        const lowerSearch = searchTerm.toLowerCase();

        let filtered;
        if (searchTerm === '') {
            filtered = this._purchaseFilterData.analyticAccounts;
        } else {
            filtered = this._purchaseFilterData.analyticAccounts.filter(a => {
                const nameMatch = (a.name && typeof a.name === 'string') ? a.name.toLowerCase().includes(lowerSearch) : false;
                const codeMatch = (a.code && typeof a.code === 'string') ? a.code.toLowerCase().includes(lowerSearch) : false;
                return nameMatch || codeMatch;
            });
        }

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete_item no_results">No analytic accounts found</div>';
        } else {
            dropdown.innerHTML = filtered.map(a => {
                const displayText = a.code ? `${a.code} - ${a.name || ''}` : (a.name || 'Unnamed');
                return `<div class="autocomplete_item" data-id="${a.id}" data-code="${a.code || ''}" data-name="${a.name || ''}">${displayText}</div>`;
            }).join('');
        }

        dropdown.classList.add('show');
    },
});