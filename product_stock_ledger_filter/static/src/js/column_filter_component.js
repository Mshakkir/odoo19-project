/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
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

        onWillStart(async () => {
            await this.loadColumns();
        });
    }

    async loadColumns() {
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
            this.state.columns = JSON.parse(savedColumns);
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

            // Update order numbers
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

            // Update order numbers
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
        const table = document.querySelector('.o_list_table');
        if (!table) return;

        const headerRow = table.querySelector('thead tr');
        const bodyRows = table.querySelectorAll('tbody tr');

        if (!headerRow) return;

        // Get all th and td elements
        const headers = Array.from(headerRow.querySelectorAll('th'));
        const allRows = Array.from(bodyRows);

        // Skip first column (checkbox) - index 0
        // Apply visibility based on column configuration
        this.state.columns.forEach((col, configIndex) => {
            const columnIndex = configIndex + 1; // +1 to skip checkbox column

            // Hide/show header
            if (headers[columnIndex]) {
                headers[columnIndex].style.display = col.visible ? '' : 'none';
            }

            // Hide/show cells in all rows
            allRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[columnIndex]) {
                    cells[columnIndex].style.display = col.visible ? '' : 'none';
                }
            });
        });

        // Reorder columns based on order property
        this.reorderColumns();
    }

    reorderColumns() {
        const table = document.querySelector('.o_list_table');
        if (!table) return;

        const headerRow = table.querySelector('thead tr');
        const bodyRows = table.querySelectorAll('tbody tr');

        if (!headerRow) return;

        // Get checkbox header (first column)
        const checkboxHeader = headerRow.querySelector('th:first-child');

        // Reorder headers
        const headers = Array.from(headerRow.querySelectorAll('th')).slice(1); // Skip checkbox
        const newHeaderOrder = [];

        this.state.columns.forEach(col => {
            const header = headers.find(h => {
                const fieldName = h.getAttribute('data-name');
                return fieldName === col.name;
            });
            if (header) {
                newHeaderOrder.push(header);
            }
        });

        // Clear and rebuild header row
        headerRow.innerHTML = '';
        headerRow.appendChild(checkboxHeader);
        newHeaderOrder.forEach(h => headerRow.appendChild(h));

        // Reorder body cells
        bodyRows.forEach(row => {
            const checkboxCell = row.querySelector('td:first-child');
            const cells = Array.from(row.querySelectorAll('td')).slice(1); // Skip checkbox
            const newCellOrder = [];

            this.state.columns.forEach(col => {
                const cell = cells.find(c => {
                    const fieldName = c.getAttribute('name');
                    return fieldName === col.name;
                });
                if (cell) {
                    newCellOrder.push(cell);
                }
            });

            // Clear and rebuild row
            row.innerHTML = '';
            row.appendChild(checkboxCell);
            newCellOrder.forEach(c => row.appendChild(c));
        });
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

// Register the component
registry.category("main_components").add("ColumnFilterComponent", {
    Component: ColumnFilterComponent,
});