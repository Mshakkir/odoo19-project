/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ColumnFilterComponent extends Component {
    static template = "product_stock_ledger_filter.ColumnFilterDropdown";

    setup() {
        this.state = useState({
            isOpen: false,
            columns: [],
            searchQuery: "",
        });

        this.localStorage = useService("local_storage");

        onMounted(() => {
            this.loadColumns();
        });
    }

    loadColumns() {
        // Default column configuration matching the list view order
        const defaultColumns = [
            { name: 'product_id', label: 'Product', visible: true, order: 1 },
            { name: 'warehouse_id', label: 'Warehouse', visible: true, order: 2 },
            { name: 'date', label: 'Date', visible: true, order: 3 },
            { name: 'voucher', label: 'Voucher', visible: true, order: 4 },
            { name: 'particulars', label: 'Particulars', visible: true, order: 5 },
            { name: 'type', label: 'Type', visible: true, order: 6 },
            { name: 'rec_qty', label: 'Rec. Qty', visible: true, order: 7 },
            { name: 'rec_rate', label: 'Rec. Rate', visible: true, order: 8 },
            { name: 'issue_qty', label: 'Issue Qty', visible: true, order: 9 },
            { name: 'issue_rate', label: 'Issue Rate', visible: true, order: 10 },
            { name: 'balance', label: 'Balance', visible: true, order: 11 },
            { name: 'uom', label: 'Unit', visible: true, order: 12 },
            { name: 'invoice_status', label: 'Invoice Status', visible: true, order: 13 },
        ];

        // Load saved preferences from localStorage
        const savedColumns = this.localStorage.getItem('ledger_column_filter');

        if (savedColumns) {
            try {
                this.state.columns = JSON.parse(savedColumns);
            } catch (e) {
                console.error('Error parsing saved columns:', e);
                this.state.columns = defaultColumns;
            }
        } else {
            this.state.columns = defaultColumns;
        }

        // Sort by order
        this.state.columns.sort((a, b) => a.order - b.order);
    }

    toggleDropdown() {
        this.state.isOpen = !this.state.isOpen;
    }

    toggleColumn(column) {
        column.visible = !column.visible;
        this.saveAndApply();
    }

    toggleAll(visible) {
        this.state.columns.forEach(col => {
            col.visible = visible;
        });
        this.saveAndApply();
    }

    moveColumnUp(index) {
        if (index > 0) {
            const temp = this.state.columns[index];
            this.state.columns[index] = this.state.columns[index - 1];
            this.state.columns[index - 1] = temp;

            this.state.columns.forEach((col, idx) => {
                col.order = idx + 1;
            });

            this.saveAndApply();
        }
    }

    moveColumnDown(index) {
        if (index < this.state.columns.length - 1) {
            const temp = this.state.columns[index];
            this.state.columns[index] = this.state.columns[index + 1];
            this.state.columns[index + 1] = temp;

            this.state.columns.forEach((col, idx) => {
                col.order = idx + 1;
            });

            this.saveAndApply();
        }
    }

    resetToDefault() {
        this.localStorage.removeItem('ledger_column_filter');
        this.loadColumns();
        this.applyColumnFilter();
    }

    saveAndApply() {
        // Save to localStorage
        this.localStorage.setItem('ledger_column_filter', JSON.stringify(this.state.columns));

        // Apply to current view
        this.applyColumnFilter();
    }

    applyColumnFilter() {
        // Use a small delay to ensure DOM is ready
        setTimeout(() => {
            const table = document.querySelector('.o_list_table');
            if (!table) return;

            const headerRow = table.querySelector('thead tr');
            const bodyRows = table.querySelectorAll('tbody tr');

            if (!headerRow) return;

            const headers = Array.from(headerRow.querySelectorAll('th'));
            const allRows = Array.from(bodyRows);

            // Apply visibility
            this.state.columns.forEach((col, configIndex) => {
                const columnIndex = configIndex + 1;

                if (headers[columnIndex]) {
                    headers[columnIndex].style.display = col.visible ? '' : 'none';
                }

                allRows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells[columnIndex]) {
                        cells[columnIndex].style.display = col.visible ? '' : 'none';
                    }
                });
            });
        }, 100);
    }

    get filteredColumns() {
        if (!this.state.searchQuery) {
            return this.state.columns;
        }

        const query = this.state.searchQuery.toLowerCase();
        return this.state.columns.filter(col =>
            col.label.toLowerCase().includes(query)
        );
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }
}