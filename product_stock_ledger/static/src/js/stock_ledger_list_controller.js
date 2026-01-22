/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

export class StockLedgerListController extends ListController {
    setup() {
        super.setup();
        this.state = useState({
            filters: {
                product_id: '',
                warehouse_id: '',
                voucher: '',
                particulars: '',
                type: '',
                invoice_status: '',
                date_from: '',
                date_to: '',
            }
        });
    }

    /**
     * Apply filters to the domain
     */
    applyFilters() {
        const domain = [];

        if (this.state.filters.product_id) {
            domain.push(['product_id', 'ilike', this.state.filters.product_id]);
        }
        if (this.state.filters.warehouse_id) {
            domain.push(['warehouse_id', 'ilike', this.state.filters.warehouse_id]);
        }
        if (this.state.filters.voucher) {
            domain.push(['voucher', 'ilike', this.state.filters.voucher]);
        }
        if (this.state.filters.particulars) {
            domain.push(['particulars', 'ilike', this.state.filters.particulars]);
        }
        if (this.state.filters.type) {
            domain.push(['type', 'ilike', this.state.filters.type]);
        }
        if (this.state.filters.invoice_status) {
            domain.push(['invoice_status', 'ilike', this.state.filters.invoice_status]);
        }
        if (this.state.filters.date_from) {
            domain.push(['date', '>=', this.state.filters.date_from + ' 00:00:00']);
        }
        if (this.state.filters.date_to) {
            domain.push(['date', '<=', this.state.filters.date_to + ' 23:59:59']);
        }

        // Apply the domain to the model
        this.model.root.domain = domain;
        this.model.root.load();
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.state.filters = {
            product_id: '',
            warehouse_id: '',
            voucher: '',
            particulars: '',
            type: '',
            invoice_status: '',
            date_from: '',
            date_to: '',
        };
        this.model.root.domain = [];
        this.model.root.load();
    }

    /**
     * Handle filter input changes
     */
    onFilterChange(field, event) {
        this.state.filters[field] = event.target.value;
        this.applyFilters();
    }
}

// Register the custom controller
export const stockLedgerListView = {
    ...listView,
    Controller: StockLedgerListController,
};

registry.category("views").add("stock_ledger_list", stockLedgerListView);