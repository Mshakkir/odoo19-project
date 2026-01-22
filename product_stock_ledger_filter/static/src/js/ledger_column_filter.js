/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this._ledgerFilterElement = null;

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
                        <!-- Product Filter -->
                        <div class="filter_group">
                            <label>Product</label>
                            <input type="text" class="form-control filter_input" id="filter_product_${timestamp}" placeholder="Product..." />
                        </div>

                        <!-- Warehouse Filter -->
                        <div class="filter_group">
                            <label>Warehouse</label>
                            <select class="form-control filter_select" id="filter_warehouse_${timestamp}">
                                <option value="">All Warehouses</option>
                            </select>
                        </div>

                        <!-- Date Range Filter -->
                        <div class="filter_group date_group">
                            <label>Date</label>
                            <div class="date_inputs">
                                <input type="date" class="form-control filter_date" id="filter_date_from_${timestamp}" value="${dateFrom}" />
                                <span class="date_sep">→</span>
                                <input type="date" class="form-control filter_date" id="filter_date_to_${timestamp}" value="${dateTo}" />
                            </div>
                        </div>

                        <!-- Voucher Filter -->
                        <div class="filter_group">
                            <label>Voucher</label>
                            <input type="text" class="form-control filter_input" id="filter_voucher_${timestamp}" placeholder="Voucher..." />
                        </div>

                        <!-- Particulars Filter -->
                        <div class="filter_group">
                            <label>Particulars</label>
                            <select class="form-control filter_select" id="filter_particulars_${timestamp}">
                                <option value="">All Particulars</option>
                            </select>
                        </div>

                        <!-- Type Filter -->
                        <div class="filter_group">
                            <label>Type</label>
                            <select class="form-control filter_select" id="filter_type_${timestamp}">
                                <option value="">All Types</option>
                                <option value="Receipts">Receipts</option>
                                <option value="Delivery">Delivery</option>
                                <option value="Internal Transfer">Internal Transfer</option>
                            </select>
                        </div>

                        <!-- Invoice Status Filter -->
                        <div class="filter_group">
                            <label>Invoice Status</label>
                            <select class="form-control filter_select" id="filter_invoice_status_${timestamp}">
                                <option value="">All Status</option>
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
            warehouses.forEach(wh => {
                const option = document.createElement('option');
                option.value = wh.id;
                option.textContent = wh.name;
                warehouseSelect.appendChild(option);
            });

        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    },

    attachFilterEvents(timestamp) {
        const productInput = document.getElementById(`filter_product_${timestamp}`);
        const warehouseSelect = document.getElementById(`filter_warehouse_${timestamp}`);
        const dateFromInput = document.getElementById(`filter_date_from_${timestamp}`);
        const dateToInput = document.getElementById(`filter_date_to_${timestamp}`);
        const voucherInput = document.getElementById(`filter_voucher_${timestamp}`);
        const particularsSelect = document.getElementById(`filter_particulars_${timestamp}`);
        const typeSelect = document.getElementById(`filter_type_${timestamp}`);
        const invoiceStatusSelect = document.getElementById(`filter_invoice_status_${timestamp}`);
        const applyBtn = document.getElementById(`apply_filter_${timestamp}`);
        const clearBtn = document.getElementById(`clear_filter_${timestamp}`);

        if (!applyBtn || !clearBtn) return;

        // Apply filter
        applyBtn.addEventListener('click', () => {
            const domain = [];

            // Product filter
            if (productInput.value.trim()) {
                domain.push(['product_id.name', 'ilike', productInput.value.trim()]);
            }

            // Warehouse filter
            if (warehouseSelect.value) {
                domain.push(['warehouse_id', '=', parseInt(warehouseSelect.value)]);
            }

            // Date range filter
            const dateFrom = dateFromInput.value;
            const dateTo = dateToInput.value;

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
            if (voucherInput.value.trim()) {
                domain.push(['voucher', 'ilike', voucherInput.value.trim()]);
            }

            // Particulars filter
            if (particularsSelect.value) {
                domain.push(['particulars', '=', particularsSelect.value]);
            }

            // Type filter
            if (typeSelect.value) {
                domain.push(['type', '=', typeSelect.value]);
            }

            // Invoice status filter
            if (invoiceStatusSelect.value) {
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
            productInput.value = '';
            warehouseSelect.value = '';
            voucherInput.value = '';
            particularsSelect.value = '';
            typeSelect.value = '';
            invoiceStatusSelect.value = '';

            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            dateFromInput.value = firstDay.toISOString().split('T')[0];
            dateToInput.value = today.toISOString().split('T')[0];

            // Reset to default domain
            if (this.model && this.model.load) {
                this.model.load({ domain: [] }).catch((error) => {
                    console.warn('Model load warning:', error);
                });
                this.notification.add("Filters cleared", { type: "info" });
            }
        });

        // Enter key to apply
        const allInputs = [productInput, warehouseSelect, dateFromInput, dateToInput, voucherInput, particularsSelect, typeSelect, invoiceStatusSelect];
        allInputs.forEach(input => {
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

// Import useService
import { useService } from "@web/core/utils/hooks";