/////** @odoo-module **/
//
//import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//
//// Patch ListController to inject date filter for Purchase Orders, RFQs and Bills
//patch(ListController.prototype, {
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this.actionService = useService("action");
//        this.orm = useService("orm");
//        this._purchaseFilterElement = null;
//        this._purchaseFilterData = {
//            warehouses: [],
//            vendors: [],
//            purchaseReps: []
//        };
//
//        onMounted(() => {
//            if (this.shouldShowPurchaseFilter()) {
//                setTimeout(() => this.loadPurchaseFilterData(), 150);
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupPurchaseFilter();
//        });
//    },
//
//    shouldShowPurchaseFilter() {
//        const resModel = this.props.resModel;
//
//        // Check if it's Purchase Orders or RFQs
//        if (resModel === 'purchase.order') {
//            const action = this.env.config;
//
//            // RFQ action
//            if (action.xmlId === 'purchase.purchase_rfq') {
//                return true;
//            }
//
//            // Purchase Order action
//            if (action.xmlId === 'purchase.purchase_form_action') {
//                return true;
//            }
//
//            // Check action name
//            if (action.displayName || action.name) {
//                const actionName = (action.displayName || action.name).toLowerCase();
//                if (actionName.includes('purchase') || actionName.includes('rfq') || actionName.includes('request for quotation')) {
//                    return true;
//                }
//            }
//
//            // Check domain for purchase states
//            if (this.props.domain) {
//                const domainStr = JSON.stringify(this.props.domain);
//                if (domainStr.includes('state') &&
//                    (domainStr.includes('purchase') || domainStr.includes('done') ||
//                     domainStr.includes('draft') || domainStr.includes('sent'))) {
//                    return true;
//                }
//            }
//
//            return true; // Show for all purchase.order views
//        }
//
//        // Check if it's Vendor Bills (account.move with in_invoice)
//        if (resModel === 'account.move') {
//            const action = this.env.config;
//
//            if (action.xmlId === 'account.action_move_in_invoice_type' ||
//                action.xmlId === 'purchase.action_vendor_bill_template') {
//                return true;
//            }
//
//            if (action.displayName || action.name) {
//                const actionName = (action.displayName || action.name).toLowerCase();
//                if (actionName.includes('bill') ||
//                    (actionName.includes('vendor') && actionName.includes('invoice'))) {
//                    return true;
//                }
//            }
//
//            if (this.props.domain) {
//                const domainStr = JSON.stringify(this.props.domain);
//                if (domainStr.includes('move_type') &&
//                    domainStr.includes('in_invoice')) {
//                    return true;
//                }
//            }
//        }
//
//        return false;
//    },
//
//    cleanupPurchaseFilter() {
//        if (this._purchaseFilterElement && this._purchaseFilterElement.parentNode) {
//            this._purchaseFilterElement.remove();
//            this._purchaseFilterElement = null;
//        }
//    },
//
//    async loadPurchaseFilterData() {
//        try {
//            // Load warehouses
//            const warehouses = await this.orm.searchRead(
//                'stock.warehouse',
//                [],
//                ['id', 'name'],
//                { limit: 100 }
//            );
//
//            // Load vendors (partners that are suppliers)
//            const vendors = await this.orm.searchRead(
//                'res.partner',
//                [['supplier_rank', '>', 0]],
//                ['id', 'name'],
//                { limit: 500, order: 'name' }
//            );
//
//            // Load purchase representatives (users)
//            const purchaseReps = await this.orm.searchRead(
//                'res.users',
//                [],
//                ['id', 'name'],
//                { limit: 100, order: 'name' }
//            );
//
//            this._purchaseFilterData = {
//                warehouses: warehouses,
//                vendors: vendors,
//                purchaseReps: purchaseReps
//            };
//
//            this.injectPurchaseDateFilter();
//        } catch (error) {
//            console.error('Error loading purchase filter data:', error);
//            this.notification.add("Error loading filter options", { type: "danger" });
//        }
//    },
//
//    getViewType() {
//        const resModel = this.props.resModel;
//        const action = this.env.config;
//
//        if (resModel === 'purchase.order') {
//            // Check if it's RFQ
//            if (action.xmlId === 'purchase.purchase_rfq') {
//                return 'rfq';
//            }
//
//            // Check domain for RFQ states
//            if (this.props.domain) {
//                const domainStr = JSON.stringify(this.props.domain);
//                if (domainStr.includes('draft') || domainStr.includes('sent')) {
//                    return 'rfq';
//                }
//            }
//
//            // Default to purchase order
//            return 'purchase_order';
//        }
//
//        if (resModel === 'account.move') {
//            return 'bill';
//        }
//
//        return 'purchase_order';
//    },
//
//    injectPurchaseDateFilter() {
//        this.cleanupPurchaseFilter();
//
//        const listTable = document.querySelector('.o_list_table');
//
//        if (!listTable) {
//            setTimeout(() => this.injectPurchaseDateFilter(), 100);
//            return;
//        }
//
//        if (document.querySelector('.purchase_date_filter_wrapper_main')) {
//            return;
//        }
//
//        const viewType = this.getViewType();
//        const timestamp = Date.now();
//
//        // Common field IDs
//        const fromId = `purchase_date_from_${timestamp}`;
//        const toId = `purchase_date_to_${timestamp}`;
//        const warehouseId = `purchase_warehouse_${timestamp}`;
//        const vendorId = `purchase_vendor_${timestamp}`;
//        const repId = `purchase_rep_${timestamp}`;
//        const orderRefId = `purchase_order_ref_${timestamp}`;
//        const vendorRefId = `purchase_vendor_ref_${timestamp}`;
//        const shippingRefId = `purchase_shipping_ref_${timestamp}`;
//        const amountId = `purchase_amount_${timestamp}`;
//        const sourceDocId = `purchase_source_doc_${timestamp}`;
//        const goodsReceiptId = `purchase_goods_receipt_${timestamp}`;
//        const billingStatusId = `purchase_billing_status_${timestamp}`;
//        const paymentStatusId = `purchase_payment_status_${timestamp}`;
//        const applyId = `purchase_apply_${timestamp}`;
//        const clearId = `purchase_clear_${timestamp}`;
//
//        const today = new Date();
//        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//        const dateFrom = firstDay.toISOString().split('T')[0];
//        const dateTo = today.toISOString().split('T')[0];
//
//        // Build warehouse options
//        const warehouseOptions = this._purchaseFilterData.warehouses
//            .map(w => `<option value="${w.id}">${w.name}</option>`)
//            .join('');
//
//        let filterHTML = '';
//
//        // Generate filter HTML based on view type
//        if (viewType === 'purchase_order' || viewType === 'rfq') {
//            // Purchase Order and RFQ filters
//            filterHTML = `
//                <div class="purchase_date_filter_container">
//                    <div class="date_filter_wrapper">
//                        <!-- Date Range Filter -->
//                        <div class="filter_group date_group">
//                            <label class="filter_label">Order Date:</label>
//                            <div class="date_input_group">
//                                <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
//                                <span class="date_separator">→</span>
//                                <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
//                            </div>
//                        </div>
//
//                        <!-- Order Reference Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Order Ref:</label>
//                            <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="${viewType === 'rfq' ? 'RFQ...' : 'PO...'}" />
//                        </div>
//
//                        <!-- Vendor Filter (Searchable) -->
//                        <div class="filter_group autocomplete_group">
//                            <label class="filter_label">Vendor:</label>
//                            <div class="autocomplete_wrapper">
//                                <input
//                                    type="text"
//                                    class="form-control autocomplete_input"
//                                    id="${vendorId}_input"
//                                    placeholder="Vendor"
//                                    autocomplete="off"
//                                />
//                                <input type="hidden" id="${vendorId}_value" />
//                                <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <!-- Vendor Reference Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Vendor Ref:</label>
//                            <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
//                        </div>
//
//                        <!-- Warehouse Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Warehouse:</label>
//                            <select class="form-select filter_select" id="${warehouseId}">
//                                <option value="">Warehouse</option>
//                                ${warehouseOptions}
//                            </select>
//                        </div>
//
//                        <!-- Shipping Reference Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Shipping Ref:</label>
//                            <input type="text" class="form-control filter_input" id="${shippingRefId}" placeholder="AWB..." />
//                        </div>
//
//                        <!-- Total Amount Filter -->
//                        <div class="filter_group amount_group">
//                            <label class="filter_label">Amount:</label>
//                            <input type="number" class="form-control amount_input" id="${amountId}" placeholder="Total Amount" step="0.01" />
//                        </div>
//
//                        <!-- Purchase Rep Filter (Searchable) -->
//                        <div class="filter_group autocomplete_group">
//                            <label class="filter_label">Purchase Rep:</label>
//                            <div class="autocomplete_wrapper">
//                                <input
//                                    type="text"
//                                    class="form-control autocomplete_input"
//                                    id="${repId}_input"
//                                    placeholder="Purchase Rep"
//                                    autocomplete="off"
//                                />
//                                <input type="hidden" id="${repId}_value" />
//                                <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <!-- Billing Status Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Billing Status:</label>
//                            <select class="form-select filter_select" id="${billingStatusId}">
//                                <option value="">Billing Status</option>
//                                <option value="no">Nothing to Bill</option>
//                                <option value="to invoice">To Invoice</option>
//                                <option value="invoiced">Fully Invoiced</option>
//                            </select>
//                        </div>
//
//                        <!-- Action Buttons -->
//                        <div class="filter_actions">
//                            <button class="btn btn-primary apply_filter_btn" id="${applyId}">Apply</button>
//                            <button class="btn btn-secondary clear_filter_btn" id="${clearId}">Clear</button>
//                        </div>
//                    </div>
//                </div>
//            `;
//        } else if (viewType === 'bill') {
//            // Vendor Bill filters
//            filterHTML = `
//                <div class="purchase_date_filter_container">
//                    <div class="date_filter_wrapper">
//                        <!-- Date Range Filter -->
//                        <div class="filter_group date_group">
//                            <label class="filter_label">Bill Date:</label>
//                            <div class="date_input_group">
//                                <input type="date" class="form-control date_input" id="${fromId}" value="${dateFrom}" placeholder="From" />
//                                <span class="date_separator">→</span>
//                                <input type="date" class="form-control date_input" id="${toId}" value="${dateTo}" placeholder="To" />
//                            </div>
//                        </div>
//
//                        <!-- Bill Number Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Bill Number:</label>
//                            <input type="text" class="form-control filter_input" id="${orderRefId}" placeholder="BILL..." />
//                        </div>
//
//                        <!-- Vendor Filter (Searchable) -->
//                        <div class="filter_group autocomplete_group">
//                            <label class="filter_label">Vendor:</label>
//                            <div class="autocomplete_wrapper">
//                                <input
//                                    type="text"
//                                    class="form-control autocomplete_input"
//                                    id="${vendorId}_input"
//                                    placeholder="Vendor"
//                                    autocomplete="off"
//                                />
//                                <input type="hidden" id="${vendorId}_value" />
//                                <div class="autocomplete_dropdown" id="${vendorId}_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <!-- Warehouse Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Warehouse:</label>
//                            <select class="form-select filter_select" id="${warehouseId}">
//                                <option value="">Warehouse</option>
//                                ${warehouseOptions}
//                            </select>
//                        </div>
//
//                        <!-- Source Document Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Source Doc:</label>
//                            <input type="text" class="form-control filter_input" id="${sourceDocId}" placeholder="Source Doc..." />
//                        </div>
//
//                        <!-- Vendor Reference Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Vendor Ref:</label>
//                            <input type="text" class="form-control filter_input" id="${vendorRefId}" placeholder="Vendor Ref..." />
//                        </div>
//
//                        <!-- Total Amount Filter -->
//                        <div class="filter_group amount_group">
//                            <label class="filter_label">Amount:</label>
//                            <input type="number" class="form-control amount_input" id="${amountId}" placeholder="Total Amount" step="0.01" />
//                        </div>
//
//                        <!-- Buyer Filter (Searchable) -->
//                        <div class="filter_group autocomplete_group">
//                            <label class="filter_label">Buyer:</label>
//                            <div class="autocomplete_wrapper">
//                                <input
//                                    type="text"
//                                    class="form-control autocomplete_input"
//                                    id="${repId}_input"
//                                    placeholder="Buyer"
//                                    autocomplete="off"
//                                />
//                                <input type="hidden" id="${repId}_value" />
//                                <div class="autocomplete_dropdown" id="${repId}_dropdown"></div>
//                            </div>
//                        </div>
//
//                        <!-- Shipping Reference Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Shipping Ref:</label>
//                            <input type="text" class="form-control filter_input" id="${shippingRefId}" placeholder="AWB..." />
//                        </div>
//
//                        <!-- Goods Receipt Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Goods Receipt:</label>
//                            <input type="text" class="form-control filter_input" id="${goodsReceiptId}" placeholder="Goods Receipt..." />
//                        </div>
//
//                        <!-- Payment Status Filter -->
//                        <div class="filter_group">
//                            <label class="filter_label">Payment Status:</label>
//                            <select class="form-select filter_select" id="${paymentStatusId}">
//                                <option value="">Payment Status</option>
//                                <option value="not_paid">Not Paid</option>
//                                <option value="in_payment">In Payment</option>
//                                <option value="paid">Paid</option>
//                                <option value="partial">Partial</option>
//                                <option value="reversed">Reversed</option>
//                            </select>
//                        </div>
//
//                        <!-- Action Buttons -->
//                        <div class="filter_actions">
//                            <button class="btn btn-primary apply_filter_btn" id="${applyId}">Apply</button>
//                            <button class="btn btn-secondary clear_filter_btn" id="${clearId}">Clear</button>
//                        </div>
//                    </div>
//                </div>
//            `;
//        }
//
//        const filterDiv = document.createElement('div');
//        filterDiv.className = 'purchase_date_filter_wrapper_main';
//        filterDiv.innerHTML = filterHTML;
//
//        listTable.parentElement.insertBefore(filterDiv, listTable);
//        this._purchaseFilterElement = filterDiv;
//
//        // Setup autocomplete
//        this.setupPurchaseAutocomplete(vendorId, this._purchaseFilterData.vendors);
//        this.setupPurchaseAutocomplete(repId, this._purchaseFilterData.purchaseReps);
//
//        this.attachPurchaseFilterEvents(
//            fromId, toId, warehouseId, vendorId, repId,
//            orderRefId, vendorRefId, shippingRefId, amountId,
//            sourceDocId, goodsReceiptId, billingStatusId, paymentStatusId,
//            applyId, clearId, viewType
//        );
//    },
//
//    setupPurchaseAutocomplete(fieldId, dataList) {
//        const input = document.getElementById(`${fieldId}_input`);
//        const hiddenValue = document.getElementById(`${fieldId}_value`);
//        const dropdown = document.getElementById(`${fieldId}_dropdown`);
//
//        if (!input || !dropdown || !hiddenValue) return;
//
//        input.addEventListener('focus', () => {
//            this.filterPurchaseAutocomplete(fieldId, dataList, '');
//            dropdown.classList.add('show');
//        });
//
//        input.addEventListener('input', (e) => {
//            const searchTerm = e.target.value;
//            hiddenValue.value = '';
//            this.filterPurchaseAutocomplete(fieldId, dataList, searchTerm);
//            dropdown.classList.add('show');
//        });
//
//        input.addEventListener('keypress', (e) => {
//            if (e.key === 'Enter') {
//                dropdown.classList.remove('show');
//                const applyBtn = document.querySelector('.apply_filter_btn');
//                if (applyBtn) {
//                    applyBtn.click();
//                }
//            }
//        });
//
//        document.addEventListener('click', (e) => {
//            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
//                dropdown.classList.remove('show');
//            }
//        });
//    },
//
//    filterPurchaseAutocomplete(fieldId, dataList, searchTerm) {
//        const dropdown = document.getElementById(`${fieldId}_dropdown`);
//        const input = document.getElementById(`${fieldId}_input`);
//        const hiddenValue = document.getElementById(`${fieldId}_value`);
//
//        if (!dropdown) return;
//
//        const lowerSearch = searchTerm.toLowerCase();
//        const filtered = dataList.filter(item =>
//            item.name.toLowerCase().includes(lowerSearch)
//        );
//
//        if (filtered.length === 0) {
//            dropdown.innerHTML = '<div class="autocomplete_item no_results">No results found</div>';
//            return;
//        }
//
//        dropdown.innerHTML = filtered.map(item => `
//            <div class="autocomplete_item" data-id="${item.id}" data-name="${item.name}">
//                ${item.name}
//            </div>
//        `).join('');
//
//        dropdown.querySelectorAll('.autocomplete_item:not(.no_results)').forEach(item => {
//            item.addEventListener('click', () => {
//                const id = item.getAttribute('data-id');
//                const name = item.getAttribute('data-name');
//                input.value = name;
//                hiddenValue.value = id;
//                dropdown.classList.remove('show');
//            });
//        });
//    },
//
//    attachPurchaseFilterEvents(
//        fromId, toId, warehouseId, vendorId, repId,
//        orderRefId, vendorRefId, shippingRefId, amountId,
//        sourceDocId, goodsReceiptId, billingStatusId, paymentStatusId,
//        applyId, clearId, viewType
//    ) {
//        const dateFromInput = document.getElementById(fromId);
//        const dateToInput = document.getElementById(toId);
//        const warehouseSelect = document.getElementById(warehouseId);
//        const vendorValue = document.getElementById(`${vendorId}_value`);
//        const vendorInput = document.getElementById(`${vendorId}_input`);
//        const repValue = document.getElementById(`${repId}_value`);
//        const repInput = document.getElementById(`${repId}_input`);
//        const orderRefInput = document.getElementById(orderRefId);
//        const vendorRefInput = document.getElementById(vendorRefId);
//        const shippingRefInput = document.getElementById(shippingRefId);
//        const amountInput = document.getElementById(amountId);
//        const sourceDocInput = document.getElementById(sourceDocId);
//        const goodsReceiptInput = document.getElementById(goodsReceiptId);
//        const billingStatusSelect = document.getElementById(billingStatusId);
//        const paymentStatusSelect = document.getElementById(paymentStatusId);
//        const applyBtn = document.getElementById(applyId);
//        const clearBtn = document.getElementById(clearId);
//
//        if (!dateFromInput || !dateToInput || !applyBtn || !clearBtn) return;
//
//        // Apply filter function
//        const applyFilter = () => {
//            try {
//                const dateFrom = dateFromInput.value;
//                const dateTo = dateToInput.value;
//
//                if (!dateFrom || !dateTo) {
//                    this.notification.add("Please select both dates", { type: "warning" });
//                    return;
//                }
//
//                if (dateFrom > dateTo) {
//                    this.notification.add("Start date must be before end date", { type: "warning" });
//                    return;
//                }
//
//                let domain = [];
//                let resModel = '';
//                let actionName = '';
//                let context = {};
//
//                if (viewType === 'purchase_order') {
//                    domain = [
//                        ['date_order', '>=', dateFrom + ' 00:00:00'],
//                        ['date_order', '<=', dateTo + ' 23:59:59'],
//                        ['state', 'in', ['purchase', 'done']]
//                    ];
//                    resModel = 'purchase.order';
//                    actionName = 'Purchase Orders';
//                } else if (viewType === 'rfq') {
//                    domain = [
//                        ['date_order', '>=', dateFrom + ' 00:00:00'],
//                        ['date_order', '<=', dateTo + ' 23:59:59'],
//                        ['state', 'in', ['draft', 'sent', 'to approve']]
//                    ];
//                    resModel = 'purchase.order';
//                    actionName = 'Request for Quotations';
//                } else if (viewType === 'bill') {
//                    domain = [
//                        ['invoice_date', '>=', dateFrom],
//                        ['invoice_date', '<=', dateTo],
//                        ['move_type', '=', 'in_invoice'],
//                        ['state', '!=', 'cancel']
//                    ];
//                    resModel = 'account.move';
//                    actionName = 'Vendor Bills';
//                    context = {
//                        'default_move_type': 'in_invoice',
//                    };
//                }
//
//                // Common filters for all view types
//
//                // Vendor filter
//                if (vendorValue.value) {
//                    domain.push(['partner_id', '=', parseInt(vendorValue.value)]);
//                }
//
//                // Purchase rep/buyer filter
//                if (repValue.value) {
//                    if (viewType === 'bill') {
//                        // Use buyer_id for bills
//                        domain.push(['buyer_id', '=', parseInt(repValue.value)]);
//                    } else {
//                        domain.push(['user_id', '=', parseInt(repValue.value)]);
//                    }
//                }
//
//                // Reference filter (Order/Bill number)
//                if (orderRefInput.value.trim()) {
//                    domain.push(['name', 'ilike', orderRefInput.value.trim()]);
//                }
//
//                // Vendor reference filter
//                if (vendorRefInput.value.trim()) {
//                    if (viewType === 'bill') {
//                        domain.push(['ref', 'ilike', vendorRefInput.value.trim()]);
//                    } else {
//                        domain.push(['partner_ref', 'ilike', vendorRefInput.value.trim()]);
//                    }
//                }
//
//                // Amount filter
//                if (amountInput.value) {
//                    const exactAmount = parseFloat(amountInput.value);
//                    domain.push(['amount_total', '=', exactAmount]);
//                }
//
//                // View-specific filters
//                if (viewType === 'purchase_order' || viewType === 'rfq') {
//                    // Warehouse filter
//                    if (warehouseSelect.value) {
//                        domain.push(['picking_type_id.warehouse_id', '=', parseInt(warehouseSelect.value)]);
//                    }
//
//                    // Shipping reference filter
//                    if (shippingRefInput.value.trim()) {
//                        domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
//                    }
//
//                    // Billing status filter
//                    if (billingStatusSelect && billingStatusSelect.value) {
//                        domain.push(['invoice_status', '=', billingStatusSelect.value]);
//                    }
//                } else if (viewType === 'bill') {
//                    // Warehouse filter for bills
//                    if (warehouseSelect.value) {
//                        domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
//                    }
//
//                    // Source document filter
//                    if (sourceDocInput && sourceDocInput.value.trim()) {
//                        domain.push(['invoice_origin', 'ilike', sourceDocInput.value.trim()]);
//                    }
//
//                    // Shipping reference filter (awb_number field)
//                    if (shippingRefInput.value.trim()) {
//                        domain.push(['awb_number', 'ilike', shippingRefInput.value.trim()]);
//                    }
//
//                    // Goods Receipt filter (goods_receipt_number field)
//                    if (goodsReceiptInput && goodsReceiptInput.value.trim()) {
//                        domain.push(['goods_receipt_number', 'ilike', goodsReceiptInput.value.trim()]);
//                    }
//
//                    // Payment status filter
//                    if (paymentStatusSelect && paymentStatusSelect.value) {
//                        domain.push(['payment_state', '=', paymentStatusSelect.value]);
//                    }
//                }
//
//                // Check if model and controller still exist before reloading
//                if (this.model && this.model.load) {
//                    this.model.load({ domain: domain, context: context }).catch((error) => {
//                        console.warn('Model load warning:', error);
//                    });
//                    this.notification.add("Filters applied successfully", { type: "success" });
//                }
//            } catch (error) {
//                console.error('Filter error:', error);
//                this.notification.add("Error applying filters: " + error.message, { type: "danger" });
//            }
//        };
//
//        // Click on Apply button
//        applyBtn.addEventListener('click', applyFilter);
//
//        // Press Enter on any input field to apply filter
//        const allInputs = [
//            dateFromInput, dateToInput, warehouseSelect, vendorInput, repInput,
//            orderRefInput, vendorRefInput, shippingRefInput, amountInput
//        ];
//
//        // Add bill-specific inputs if they exist
//        if (sourceDocInput) allInputs.push(sourceDocInput);
//        if (goodsReceiptInput) allInputs.push(goodsReceiptInput);
//        if (billingStatusSelect) allInputs.push(billingStatusSelect);
//        if (paymentStatusSelect) allInputs.push(paymentStatusSelect);
//
//        allInputs.forEach(input => {
//            if (input) {
//                input.addEventListener('keypress', (e) => {
//                    if (e.key === 'Enter') {
//                        e.preventDefault();
//                        applyFilter();
//                    }
//                });
//            }
//        });
//
//        // Clear filter function
//        const clearFilter = () => {
//            try {
//                const today = new Date();
//                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//                dateFromInput.value = firstDay.toISOString().split('T')[0];
//                dateToInput.value = today.toISOString().split('T')[0];
//                warehouseSelect.value = '';
//                vendorInput.value = '';
//                vendorValue.value = '';
//                repInput.value = '';
//                repValue.value = '';
//                orderRefInput.value = '';
//                vendorRefInput.value = '';
//                shippingRefInput.value = '';
//                amountInput.value = '';
//
//                if (sourceDocInput) sourceDocInput.value = '';
//                if (goodsReceiptInput) goodsReceiptInput.value = '';
//                if (billingStatusSelect) billingStatusSelect.value = '';
//                if (paymentStatusSelect) paymentStatusSelect.value = '';
//
//                let domain = [];
//                let context = {};
//
//                if (viewType === 'purchase_order') {
//                    domain = [['state', 'in', ['purchase', 'done']]];
//                } else if (viewType === 'rfq') {
//                    domain = [['state', 'in', ['draft', 'sent', 'to approve']]];
//                } else if (viewType === 'bill') {
//                    domain = [['move_type', '=', 'in_invoice']];
//                    context = {
//                        'default_move_type': 'in_invoice',
//                    };
//                }
//
//                // Check if model and controller still exist before reloading
//                if (this.model && this.model.load) {
//                    this.model.load({ domain: domain, context: context }).catch((error) => {
//                        console.warn('Model load warning during clear:', error);
//                    });
//                    this.notification.add("Filters cleared successfully", { type: "info" });
//                }
//            } catch (error) {
//                console.error('Clear filter error:', error);
//                this.notification.add("Error clearing filters: " + error.message, { type: "danger" });
//            }
//        };
//
//        // Clear button click
//        clearBtn.addEventListener('click', clearFilter);
//
//        // ESC key to clear filter
//        document.addEventListener('keydown', (e) => {
//            if (e.key === 'Escape') {
//                clearFilter();
//            }
//        });
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
            warehouses: [],
            customers: [],
            salespersons: [],
            analyticAccounts: [],
        };
        this._listeners = [];

        onMounted(async () => {
            if (this.shouldShowFilter()) {
                await this.loadFilterData();
                const timer = setInterval(() => {
                    if (this.injectDateFilter()) clearInterval(timer);
                }, 400);
            }
        });

        onWillUnmount(() => this.cleanupFilter());
    },

    /* --------------------------------------------------------- */
    /* FILTER VISIBILITY */
    /* --------------------------------------------------------- */
    shouldShowFilter() {
        const resModel = this.props.resModel;
        const ctx = this.props.context || {};

        if (['sale.order', 'purchase.order'].includes(resModel)) return true;

        if (resModel === 'account.move') {
            const type = ctx.default_move_type || ctx.type;
            return ['out_invoice', 'in_invoice'].includes(type);
        }
        return false;
    },

    cleanupFilter() {
        this._listeners.forEach(l => {
            try { l.element.removeEventListener(l.event, l.handler); } catch {}
        });
        this._listeners = [];
    },

    addEventListener(el, event, handler) {
        if (el) {
            el.addEventListener(event, handler);
            this._listeners.push({ element: el, event, handler });
        }
    },

    /* --------------------------------------------------------- */
    /* LOAD MASTER DATA */
    /* --------------------------------------------------------- */
    async loadFilterData() {
        const [warehouses, customers, salespersons, analyticAccounts] =
            await Promise.all([
                this.orm.searchRead('stock.warehouse', [], ['id', 'name']),
                this.orm.searchRead('res.partner', [['customer_rank', '>', 0]], ['id', 'name']),
                this.orm.searchRead('res.users', [], ['id', 'name']),
                this.orm.searchRead('account.analytic.account', [], ['id', 'name', 'code']),
            ]);

        this._filterData = { warehouses, customers, salespersons, analyticAccounts };
    },

    /* --------------------------------------------------------- */
    /* UI INJECTION */
    /* --------------------------------------------------------- */
    injectDateFilter() {
        if (this._filterInjected) return true;

        const table = document.querySelector('.o_list_table');
        if (!table) return false;

        const html = `
        <div class="sale_date_filter_wrapper_main">
            <input type="text" class="filter_analytic_input" placeholder="Analytic Account"/>
            <div class="autocomplete_dropdown filter_analytic_dropdown"></div>
            <button class="btn btn-primary apply_filter_btn">Apply</button>
            <button class="btn btn-secondary clear_filter_btn">Clear</button>
        </div>`;

        const div = document.createElement('div');
        div.innerHTML = html;
        table.parentNode.insertBefore(div, table);

        this._filterInjected = true;
        this.attachFilterListeners();
        return true;
    },

    /* --------------------------------------------------------- */
    /* FILTER LOGIC */
    /* --------------------------------------------------------- */
    attachFilterListeners() {
        const resModel = this.props.resModel;
        const ctx = this.props.context || {};

        const isSale = resModel === 'sale.order';
        const isPurchase = resModel === 'purchase.order';
        const isInvoice = resModel === 'account.move';
        const isCustomerInvoice = isInvoice && ctx.default_move_type === 'out_invoice';
        const isVendorBill = isInvoice && ctx.default_move_type === 'in_invoice';

        const analyticInput = document.querySelector('.filter_analytic_input');
        const analyticDropdown = document.querySelector('.filter_analytic_dropdown');
        const applyBtn = document.querySelector('.apply_filter_btn');
        const clearBtn = document.querySelector('.clear_filter_btn');

        let analyticId = null;

        this.addEventListener(analyticInput, 'input', e => {
            const term = e.target.value.toLowerCase();
            const rows = this._filterData.analyticAccounts.filter(a =>
                a.name.toLowerCase().includes(term) ||
                (a.code && a.code.toLowerCase().includes(term))
            );

            analyticDropdown.innerHTML = rows.length
                ? rows.map(a =>
                    `<div class="autocomplete_item" data-id="${a.id}">
                        ${a.code ? a.code + ' - ' : ''}${a.name}
                     </div>`).join('')
                : `<div class="autocomplete_item no_results">No results</div>`;

            analyticDropdown.classList.add('show');
        });

        this.addEventListener(analyticDropdown, 'click', e => {
            const item = e.target.closest('.autocomplete_item');
            if (!item || item.classList.contains('no_results')) return;
            analyticId = parseInt(item.dataset.id);
            analyticInput.value = item.textContent;
            analyticDropdown.classList.remove('show');
        });

        /* ---------------- APPLY FILTER ---------------- */
        this.addEventListener(applyBtn, 'click', async () => {
            let domain = [];

            if (isCustomerInvoice) domain.push(['move_type', '=', 'out_invoice']);
            if (isVendorBill) domain.push(['move_type', '=', 'in_invoice']);

            if (analyticId) {
                const applyAnalytic = async (lineModel, moveField) => {
                    const lines = await this.orm.searchRead(
                        lineModel,
                        [['analytic_distribution', '!=', false]],
                        [moveField, 'analytic_distribution'],
                        { limit: 5000 }
                    );

                    const ids = [];
                    for (const l of lines) {
                        const dist = typeof l.analytic_distribution === 'string'
                            ? JSON.parse(l.analytic_distribution)
                            : l.analytic_distribution;

                        if (dist?.[analyticId]) {
                            ids.push(l[moveField][0]);
                        }
                    }
                    domain.push(ids.length ? ['id', 'in', [...new Set(ids)]] : ['id', '=', -1]);
                };

                if (isSale) await applyAnalytic('sale.order.line', 'order_id');
                else if (isPurchase) await applyAnalytic('purchase.order.line', 'order_id');
                else if (isCustomerInvoice) await applyAnalytic('account.move.line', 'move_id');
                else if (isVendorBill) await applyAnalytic('account.move.line', 'move_id');
            }

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: resModel,
                views: [[false, 'list'], [false, 'form']],
                domain,
                context: ctx,
                target: 'current',
            });

            this.notification.add("Filter applied", { type: "success" });
        });

        /* ---------------- CLEAR FILTER ---------------- */
        this.addEventListener(clearBtn, 'click', () => {
            analyticInput.value = '';
            analyticId = null;

            const domain = isCustomerInvoice
                ? [['move_type', '=', 'out_invoice']]
                : isVendorBill
                ? [['move_type', '=', 'in_invoice']]
                : [];

            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: resModel,
                views: [[false, 'list'], [false, 'form']],
                domain,
                context: ctx,
                target: 'current',
            });
        });
    },
});
