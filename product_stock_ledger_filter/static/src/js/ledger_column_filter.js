/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this._ledgerFilterElement = null;
        this._productAutocompleteTimeout = null;
        this._selectedProductId = null;  // Track selected product id for domain

        onMounted(() => {
            if (this.shouldShowLedgerFilter()) {
                setTimeout(() => this.injectLedgerFilterBar(), 200);
            }
        });

        onWillUnmount(() => {
            this.cleanupLedgerFilter();
        });
    },

    shouldShowLedgerFilter() {
        const resModel = this.props.resModel;
        return resModel === 'product.stock.ledger.line';
    },

    cleanupLedgerFilter() {
        if (this._ledgerFilterElement && this._ledgerFilterElement.parentNode) {
            this._ledgerFilterElement.remove();
            this._ledgerFilterElement = null;
        }
        // Remove any leftover autocomplete dropdown
        const existing = document.querySelector('.ledger_product_autocomplete');
        if (existing) existing.remove();

        // Clear debounce timer
        if (this._productAutocompleteTimeout) {
            clearTimeout(this._productAutocompleteTimeout);
            this._productAutocompleteTimeout = null;
        }
    },

    injectLedgerFilterBar() {
        this.cleanupLedgerFilter();

        const listTable = document.querySelector('.o_list_table');
        if (!listTable) {
            setTimeout(() => this.injectLedgerFilterBar(), 100);
            return;
        }

        if (document.querySelector('.ledger_filter_bar')) {
            return;
        }

        const timestamp = Date.now();
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateFrom = firstDay.toISOString().split('T')[0];
        const dateTo = today.toISOString().split('T')[0];

        const filterHTML = `
            <div class="ledger_filter_bar">
                <div class="ledger_filter_container">
                    <div class="filter_row">
                        <!-- Product Filter with Autocomplete -->
                        <div class="filter_group ledger_product_filter_group" style="position:relative;">
                            <input
                                type="text"
                                class="form-control filter_input"
                                id="filter_product_${timestamp}"
                                placeholder="Product name or code"
                                autocomplete="off"
                            />
                            <div
                                class="ledger_product_autocomplete"
                                id="product_autocomplete_${timestamp}"
                                style="display:none; position:absolute; top:100%; left:0; right:0; z-index:9999;
                                       background:#fff; border:1px solid #ced4da; border-top:none;
                                       border-radius:0 0 4px 4px; max-height:240px; overflow-y:auto;
                                       box-shadow:0 4px 8px rgba(0,0,0,0.1);"
                            ></div>
                        </div>

                        <!-- Warehouse Filter -->
                        <div class="filter_group">
                            <select class="form-control filter_select" id="filter_warehouse_${timestamp}">
                                <option value="">Warehouse</option>
                            </select>
                        </div>

                        <!-- Date Range Filter -->
                        <div class="filter_group date_group">
                            <div class="date_inputs">
                                <input type="date" class="form-control filter_date" id="filter_date_from_${timestamp}" value="${dateFrom}" />
                                <span class="date_sep">&#8594;</span>
                                <input type="date" class="form-control filter_date" id="filter_date_to_${timestamp}" value="${dateTo}" />
                            </div>
                        </div>

                        <!-- Voucher Filter -->
                        <div class="filter_group">
                            <input type="text" class="form-control filter_input" id="filter_voucher_${timestamp}" placeholder="Voucher" />
                        </div>

                        <!-- Type Filter -->
                        <div class="filter_group">
                            <select class="form-control filter_select" id="filter_type_${timestamp}">
                                <option value="">Type</option>
                                <option value="Receipts">Receipts</option>
                                <option value="Delivery">Delivery</option>
                                <option value="Internal Transfer">Internal Transfer</option>
                            </select>
                        </div>

                        <!-- Invoice Status Filter -->
                        <div class="filter_group">
                            <select class="form-control filter_select" id="filter_invoice_status_${timestamp}">
                                <option value="">Invoice Status</option>
                                <option value="Invoiced">Invoiced</option>
                                <option value="Not Invoiced">Not Invoiced</option>
                                <option value="To Invoice">To Invoice</option>
                            </select>
                        </div>

                        <!-- Action Buttons -->
                        <div class="filter_actions">
                            <button class="btn btn-primary apply_btn" id="apply_filter_${timestamp}">Apply</button>
                            <button class="btn btn-secondary clear_btn" id="clear_filter_${timestamp}">Clear</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const filterDiv = document.createElement('div');
        filterDiv.innerHTML = filterHTML;

        listTable.parentElement.insertBefore(filterDiv.firstElementChild, listTable);
        this._ledgerFilterElement = document.querySelector('.ledger_filter_bar');

        this.loadFilterOptions(timestamp);
        this.attachFilterEvents(timestamp);
        this.attachProductAutocomplete(timestamp);
    },

    async loadFilterOptions(timestamp) {
        try {
            // Load warehouses
            const warehouses = await this.orm.searchRead(
                'stock.warehouse',
                [],
                ['id', 'name'],
                { limit: 100 }
            );

            const warehouseSelect = document.getElementById(`filter_warehouse_${timestamp}`);
            if (warehouseSelect) {
                warehouses.forEach(wh => {
                    const option = document.createElement('option');
                    option.value = wh.id;
                    option.textContent = wh.name;
                    warehouseSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    },

    /**
     * Attaches live autocomplete to the product input.
     * Searches product.product by name OR default_code (product code).
     */
    attachProductAutocomplete(timestamp) {
        const productInput = document.getElementById(`filter_product_${timestamp}`);
        const autocompleteBox = document.getElementById(`product_autocomplete_${timestamp}`);

        if (!productInput || !autocompleteBox) return;

        const hideDropdown = () => {
            autocompleteBox.style.display = 'none';
            autocompleteBox.innerHTML = '';
        };

        const showLoading = () => {
            autocompleteBox.innerHTML = '<div style="padding:8px 12px;color:#6c757d;font-size:12px;">Searching...</div>';
            autocompleteBox.style.display = 'block';
        };

        const renderResults = (products) => {
            autocompleteBox.innerHTML = '';
            if (!products.length) {
                autocompleteBox.innerHTML = '<div style="padding:8px 12px;color:#6c757d;font-size:12px;">No products found</div>';
                autocompleteBox.style.display = 'block';
                return;
            }
            products.forEach(product => {
                const item = document.createElement('div');
                item.className = 'ledger_autocomplete_item';
                item.style.cssText = 'padding:7px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #f0f0f0;display:flex;gap:8px;align-items:center;';
                item.setAttribute('data-id', product.id);
                item.setAttribute('data-name', product.display_name || product.name);

                // Show product code badge if available
                const codeBadge = product.default_code
                    ? `<span style="background:#e9ecef;color:#495057;border-radius:3px;padding:1px 6px;font-size:11px;font-weight:600;white-space:nowrap;">[${product.default_code}]</span>`
                    : '';
                const productName = product.display_name || product.name;
                item.innerHTML = `${codeBadge}<span style="flex:1;">${productName}</span>`;

                item.addEventListener('mouseenter', () => {
                    item.style.backgroundColor = '#f0f7ff';
                });
                item.addEventListener('mouseleave', () => {
                    item.style.backgroundColor = '';
                });
                item.addEventListener('mousedown', (e) => {
                    // Use mousedown so it fires before input blur
                    e.preventDefault();
                    this._selectedProductId = product.id;
                    productInput.value = productName;
                    productInput.setAttribute('data-product-id', product.id);
                    hideDropdown();
                });
                autocompleteBox.appendChild(item);
            });
            autocompleteBox.style.display = 'block';
        };

        // Input event: search after debounce
        productInput.addEventListener('input', () => {
            const query = productInput.value.trim();

            // Clear previously selected product id when user types again
            this._selectedProductId = null;
            productInput.removeAttribute('data-product-id');

            if (!query) {
                hideDropdown();
                return;
            }

            if (this._productAutocompleteTimeout) {
                clearTimeout(this._productAutocompleteTimeout);
            }

            showLoading();

            this._productAutocompleteTimeout = setTimeout(async () => {
                try {
                    // Search by name OR product code (default_code)
                    const domain = [
                        '|',
                        ['name', 'ilike', query],
                        ['default_code', 'ilike', query],
                    ];

                    const products = await this.orm.searchRead(
                        'product.product',
                        domain,
                        ['id', 'name', 'display_name', 'default_code'],
                        { limit: 20, order: 'default_code asc, name asc' }
                    );

                    renderResults(products);
                } catch (error) {
                    console.error('Product autocomplete error:', error);
                    hideDropdown();
                }
            }, 300);  // 300ms debounce
        });

        // Hide dropdown on blur (slight delay to allow mousedown on item)
        productInput.addEventListener('blur', () => {
            setTimeout(hideDropdown, 200);
        });

        // Keyboard navigation in dropdown
        productInput.addEventListener('keydown', (e) => {
            const items = autocompleteBox.querySelectorAll('.ledger_autocomplete_item');
            if (!items.length) return;

            const active = autocompleteBox.querySelector('.ledger_autocomplete_item.active');
            let idx = Array.from(items).indexOf(active);

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (active) active.classList.remove('active');
                idx = (idx + 1) % items.length;
                items[idx].classList.add('active');
                items[idx].style.backgroundColor = '#f0f7ff';
                items[idx].scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (active) active.classList.remove('active');
                idx = (idx - 1 + items.length) % items.length;
                items[idx].classList.add('active');
                items[idx].style.backgroundColor = '#f0f7ff';
                items[idx].scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'Enter') {
                if (active) {
                    e.preventDefault();
                    e.stopPropagation();
                    const id = parseInt(active.getAttribute('data-id'));
                    const name = active.getAttribute('data-name');
                    this._selectedProductId = id;
                    productInput.value = name;
                    productInput.setAttribute('data-product-id', id);
                    hideDropdown();
                }
            } else if (e.key === 'Escape') {
                hideDropdown();
            }
        });

        // Remove active highlight when mouse leaves dropdown
        autocompleteBox.addEventListener('mouseleave', () => {
            autocompleteBox.querySelectorAll('.ledger_autocomplete_item.active').forEach(el => {
                el.classList.remove('active');
                el.style.backgroundColor = '';
            });
        });
    },

    attachFilterEvents(timestamp) {
        const productInput = document.getElementById(`filter_product_${timestamp}`);
        const warehouseSelect = document.getElementById(`filter_warehouse_${timestamp}`);
        const dateFromInput = document.getElementById(`filter_date_from_${timestamp}`);
        const dateToInput = document.getElementById(`filter_date_to_${timestamp}`);
        const voucherInput = document.getElementById(`filter_voucher_${timestamp}`);
        const typeSelect = document.getElementById(`filter_type_${timestamp}`);
        const invoiceStatusSelect = document.getElementById(`filter_invoice_status_${timestamp}`);
        const applyBtn = document.getElementById(`apply_filter_${timestamp}`);
        const clearBtn = document.getElementById(`clear_filter_${timestamp}`);

        if (!applyBtn || !clearBtn) return;

        // Trigger clear on ESC key (global)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearBtn.click();
            }
        });

        // Apply filter
        applyBtn.addEventListener('click', () => {
            const domain = [];

            // Product filter — prefer exact id match if user selected from autocomplete,
            // otherwise fall back to ilike on both name and default_code
            const rawProduct = productInput ? productInput.value.trim() : '';
            const selectedProductId = productInput
                ? parseInt(productInput.getAttribute('data-product-id') || '0')
                : 0;

            if (selectedProductId) {
                // Exact product selected from autocomplete
                domain.push(['product_id', '=', selectedProductId]);
            } else if (rawProduct) {
                // Free-text: search by name or product code
                domain.push([
                    '|',
                    ['product_id.name', 'ilike', rawProduct],
                    ['product_id.default_code', 'ilike', rawProduct],
                ]);
            }

            // Warehouse filter
            if (warehouseSelect && warehouseSelect.value) {
                domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
            }

            // Date range filter
            const dateFrom = dateFromInput ? dateFromInput.value : '';
            const dateTo = dateToInput ? dateToInput.value : '';

            if (dateFrom && dateTo) {
                if (dateFrom > dateTo) {
                    this.notification.add("Start date must be before end date", { type: "warning" });
                    return;
                }
                domain.push(['date', '>=', dateFrom + ' 00:00:00']);
                domain.push(['date', '<=', dateTo + ' 23:59:59']);
            } else if (dateFrom) {
                domain.push(['date', '>=', dateFrom + ' 00:00:00']);
            } else if (dateTo) {
                domain.push(['date', '<=', dateTo + ' 23:59:59']);
            }

            // Voucher filter
            if (voucherInput && voucherInput.value.trim()) {
                domain.push(['voucher', 'ilike', voucherInput.value.trim()]);
            }

            // Type filter
            if (typeSelect && typeSelect.value) {
                domain.push(['type', '=', typeSelect.value]);
            }

            // Invoice status filter
            if (invoiceStatusSelect && invoiceStatusSelect.value) {
                domain.push(['invoice_status', '=', invoiceStatusSelect.value]);
            }

            // Apply domain
            if (this.model && this.model.load) {
                this.model.load({ domain: domain }).catch((error) => {
                    console.warn('Model load warning:', error);
                });
                this.notification.add("Filters applied successfully", { type: "success" });
            }
        });

        // Clear filter
        clearBtn.addEventListener('click', () => {
            if (productInput) {
                productInput.value = '';
                productInput.removeAttribute('data-product-id');
            }
            this._selectedProductId = null;

            if (warehouseSelect) warehouseSelect.value = '';
            if (voucherInput) voucherInput.value = '';
            if (typeSelect) typeSelect.value = '';
            if (invoiceStatusSelect) invoiceStatusSelect.value = '';

            // Close any open autocomplete
            const autocompleteBox = document.querySelector('.ledger_product_autocomplete');
            if (autocompleteBox) {
                autocompleteBox.style.display = 'none';
                autocompleteBox.innerHTML = '';
            }

            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            if (dateFromInput) dateFromInput.value = firstDay.toISOString().split('T')[0];
            if (dateToInput) dateToInput.value = today.toISOString().split('T')[0];

            // Reset to default domain
            if (this.model && this.model.load) {
                this.model.load({ domain: [] }).catch((error) => {
                    console.warn('Model load warning:', error);
                });
                this.notification.add("Filters cleared", { type: "info" });
            }
        });

        // Enter key to apply on non-product inputs (product Enter is handled in autocomplete)
        const nonProductInputs = [warehouseSelect, dateFromInput, dateToInput, voucherInput, typeSelect, invoiceStatusSelect];
        nonProductInputs.forEach(input => {
            if (input) {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        applyBtn.click();
                    }
                });
            }
        });
    },
});




















///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//import { onMounted, onWillUnmount } from "@odoo/owl";
//
//patch(ListController.prototype, {
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this._ledgerFilterElement = null;
//
//        onMounted(() => {
//            if (this.shouldShowLedgerFilter()) {
//                setTimeout(() => this.injectLedgerFilterBar(), 200);
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupLedgerFilter();
//        });
//    },
//
//    shouldShowLedgerFilter() {
//        const resModel = this.props.resModel;
//        return resModel === 'product.stock.ledger.line';
//    },
//
//    cleanupLedgerFilter() {
//        if (this._ledgerFilterElement && this._ledgerFilterElement.parentNode) {
//            this._ledgerFilterElement.remove();
//            this._ledgerFilterElement = null;
//        }
//    },
//
//    injectLedgerFilterBar() {
//        this.cleanupLedgerFilter();
//
//        const listTable = document.querySelector('.o_list_table');
//        if (!listTable) {
//            setTimeout(() => this.injectLedgerFilterBar(), 100);
//            return;
//        }
//
//        if (document.querySelector('.ledger_filter_bar')) {
//            return;
//        }
//
//        const timestamp = Date.now();
//        const today = new Date();
//        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//        const dateFrom = firstDay.toISOString().split('T')[0];
//        const dateTo = today.toISOString().split('T')[0];
//
//        const filterHTML = `
//            <div class="ledger_filter_bar">
//                <div class="ledger_filter_container">
//                    <div class="filter_row">
//                        <!-- Product Filter -->
//                        <div class="filter_group">
//                            <input type="text" class="form-control filter_input" id="filter_product_${timestamp}" placeholder="Product" />
//                        </div>
//
//                        <!-- Warehouse Filter -->
//                        <div class="filter_group">
//                            <select class="form-control filter_select" id="filter_warehouse_${timestamp}">
//                                <option value="">Warehouse</option>
//                            </select>
//                        </div>
//
//                        <!-- Date Range Filter -->
//                        <div class="filter_group date_group">
//                            <div class="date_inputs">
//                                <input type="date" class="form-control filter_date" id="filter_date_from_${timestamp}" value="${dateFrom}" />
//                                <span class="date_sep">→</span>
//                                <input type="date" class="form-control filter_date" id="filter_date_to_${timestamp}" value="${dateTo}" />
//                            </div>
//                        </div>
//
//                        <!-- Voucher Filter -->
//                        <div class="filter_group">
//                            <input type="text" class="form-control filter_input" id="filter_voucher_${timestamp}" placeholder="Voucher" />
//                        </div>
//
//                        <!-- Type Filter -->
//                        <div class="filter_group">
//                            <select class="form-control filter_select" id="filter_type_${timestamp}">
//                                <option value="">Type</option>
//                                <option value="Receipts">Receipts</option>
//                                <option value="Delivery">Delivery</option>
//                                <option value="Internal Transfer">Internal Transfer</option>
//                            </select>
//                        </div>
//
//                        <!-- Invoice Status Filter -->
//                        <div class="filter_group">
//                            <select class="form-control filter_select" id="filter_invoice_status_${timestamp}">
//                                <option value="">Invoice Status</option>
//                                <option value="Invoiced">Invoiced</option>
//                                <option value="Not Invoiced">Not Invoiced</option>
//                                <option value="To Invoice">To Invoice</option>
//                            </select>
//                        </div>
//
//                        <!-- Action Buttons -->
//                        <div class="filter_actions">
//                            <button class="btn btn-primary apply_btn" id="apply_filter_${timestamp}">Apply</button>
//                            <button class="btn btn-secondary clear_btn" id="clear_filter_${timestamp}">Clear</button>
//                        </div>
//                    </div>
//                </div>
//            </div>
//        `;
//
//        const filterDiv = document.createElement('div');
//        filterDiv.innerHTML = filterHTML;
//
//        listTable.parentElement.insertBefore(filterDiv.firstElementChild, listTable);
//        this._ledgerFilterElement = document.querySelector('.ledger_filter_bar');
//
//        this.loadFilterOptions(timestamp);
//        this.attachFilterEvents(timestamp);
//    },
//
//    async loadFilterOptions(timestamp) {
//        try {
//            // Load warehouses
//            const warehouses = await this.orm.searchRead(
//                'stock.warehouse',
//                [],
//                ['id', 'name'],
//                { limit: 100 }
//            );
//
//            const warehouseSelect = document.getElementById(`filter_warehouse_${timestamp}`);
//            warehouses.forEach(wh => {
//                const option = document.createElement('option');
//                option.value = wh.id;
//                option.textContent = wh.name;
//                warehouseSelect.appendChild(option);
//            });
//
//        } catch (error) {
//            console.error('Error loading filter options:', error);
//        }
//    },
//
//    attachFilterEvents(timestamp) {
//        const productInput = document.getElementById(`filter_product_${timestamp}`);
//        const warehouseSelect = document.getElementById(`filter_warehouse_${timestamp}`);
//        const dateFromInput = document.getElementById(`filter_date_from_${timestamp}`);
//        const dateToInput = document.getElementById(`filter_date_to_${timestamp}`);
//        const voucherInput = document.getElementById(`filter_voucher_${timestamp}`);
//        const particularsSelect = document.getElementById(`filter_particulars_${timestamp}`);
//        const typeSelect = document.getElementById(`filter_type_${timestamp}`);
//        const invoiceStatusSelect = document.getElementById(`filter_invoice_status_${timestamp}`);
//        const applyBtn = document.getElementById(`apply_filter_${timestamp}`);
//        const clearBtn = document.getElementById(`clear_filter_${timestamp}`);
//
//        if (!applyBtn || !clearBtn) return;
//
//        // Trigger clear on ESC key
//        document.addEventListener('keydown', (e) => {
//            if (e.key === 'Escape') {
//                clearBtn.click();
//            }
//        });
//
//        // Apply filter
//        applyBtn.addEventListener('click', () => {
//            const domain = [];
//
//            // Product filter
//            if (productInput.value.trim()) {
//                domain.push(['product_id.name', 'ilike', productInput.value.trim()]);
//            }
//
//            // Warehouse filter
//            if (warehouseSelect.value) {
//                domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
//            }
//
//            // Date range filter
//            const dateFrom = dateFromInput.value;
//            const dateTo = dateToInput.value;
//
//            if (dateFrom && dateTo) {
//                if (dateFrom > dateTo) {
//                    this.notification.add("Start date must be before end date", { type: "warning" });
//                    return;
//                }
//                domain.push(['date', '>=', dateFrom + ' 00:00:00']);
//                domain.push(['date', '<=', dateTo + ' 23:59:59']);
//            } else if (dateFrom) {
//                domain.push(['date', '>=', dateFrom + ' 00:00:00']);
//            } else if (dateTo) {
//                domain.push(['date', '<=', dateTo + ' 23:59:59']);
//            }
//
//            // Voucher filter
//            if (voucherInput.value.trim()) {
//                domain.push(['voucher', 'ilike', voucherInput.value.trim()]);
//            }
//
//            // Type filter
//            if (typeSelect.value) {
//                domain.push(['type', '=', typeSelect.value]);
//            }
//
//            // Invoice status filter
//            if (invoiceStatusSelect.value) {
//                domain.push(['invoice_status', '=', invoiceStatusSelect.value]);
//            }
//
//            // Apply domain
//            if (this.model && this.model.load) {
//                this.model.load({ domain: domain }).catch((error) => {
//                    console.warn('Model load warning:', error);
//                });
//                this.notification.add("Filters applied successfully", { type: "success" });
//            }
//        });
//
//        // Clear filter
//        clearBtn.addEventListener('click', () => {
//            productInput.value = '';
//            warehouseSelect.value = '';
//            voucherInput.value = '';
//            typeSelect.value = '';
//            invoiceStatusSelect.value = '';
//
//            const today = new Date();
//            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//            dateFromInput.value = firstDay.toISOString().split('T')[0];
//            dateToInput.value = today.toISOString().split('T')[0];
//
//            // Reset to default domain
//            if (this.model && this.model.load) {
//                this.model.load({ domain: [] }).catch((error) => {
//                    console.warn('Model load warning:', error);
//                });
//                this.notification.add("Filters cleared", { type: "info" });
//            }
//        });
//
//        // Enter key to apply
//        const allInputs = [productInput, warehouseSelect, dateFromInput, dateToInput, voucherInput, typeSelect, invoiceStatusSelect];
//        allInputs.forEach(input => {
//            if (input) {
//                input.addEventListener('keypress', (e) => {
//                    if (e.key === 'Enter') {
//                        e.preventDefault();
//                        applyBtn.click();
//                    }
//                });
//            }
//        });
//    },
//});
//
//// Import useService
//import { useService } from "@web/core/utils/hooks";