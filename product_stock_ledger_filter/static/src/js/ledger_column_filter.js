/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this._ledgerFilterElement = null;
        this._ledgerFilterColumns = [];
        this._ledgerFilterStorage = null;

        onMounted(() => {
            if (this.shouldShowLedgerFilter()) {
                setTimeout(() => this.injectLedgerColumnFilter(), 200);
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

    loadLedgerColumnPreferences() {
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

        const saved = localStorage.getItem('ledger_column_preferences');
        if (saved) {
            try {
                this._ledgerFilterColumns = JSON.parse(saved);
            } catch (e) {
                this._ledgerFilterColumns = defaultColumns;
            }
        } else {
            this._ledgerFilterColumns = defaultColumns;
        }

        return this._ledgerFilterColumns.sort((a, b) => a.order - b.order);
    },

    saveLedgerColumnPreferences() {
        localStorage.setItem('ledger_column_preferences', JSON.stringify(this._ledgerFilterColumns));
    },

    injectLedgerColumnFilter() {
        this.cleanupLedgerFilter();

        const listTable = document.querySelector('.o_list_table');
        if (!listTable) {
            setTimeout(() => this.injectLedgerColumnFilter(), 100);
            return;
        }

        if (document.querySelector('.ledger_column_filter_bar')) {
            return;
        }

        this.loadLedgerColumnPreferences();

        const timestamp = Date.now();
        const filterId = `ledger_filter_${timestamp}`;
        const dropdownId = `ledger_filter_dropdown_${timestamp}`;
        const searchId = `ledger_filter_search_${timestamp}`;

        const columnItems = this._ledgerFilterColumns.map((col, idx) => `
            <div class="ledger_column_item" data-column="${col.name}" data-index="${idx}">
                <div class="column_checkbox">
                    <input type="checkbox" class="column_toggle" ${col.visible ? 'checked' : ''} />
                    <label>${col.label}</label>
                </div>
                <div class="column_actions">
                    <button class="btn-move-up" title="Move Up" ${idx === 0 ? 'disabled' : ''}><i class="fa fa-chevron-up"></i></button>
                    <button class="btn-move-down" title="Move Down" ${idx === this._ledgerFilterColumns.length - 1 ? 'disabled' : ''}><i class="fa fa-chevron-down"></i></button>
                </div>
            </div>
        `).join('');

        const visibleCount = this._ledgerFilterColumns.filter(c => c.visible).length;

        const filterHTML = `
            <div class="ledger_column_filter_bar">
                <div class="ledger_filter_container">
                    <div class="ledger_filter_content">
                        <button class="btn btn-sm btn-light ledger_filter_btn" id="${filterId}" title="Show/Hide Columns">
                            <i class="fa fa-columns"></i> Columns
                        </button>

                        <span class="ledger_filter_info">
                            ${visibleCount}/${this._ledgerFilterColumns.length} columns visible
                        </span>

                        <div class="ledger_filter_dropdown" id="${dropdownId}" style="display: none;">
                            <div class="ledger_filter_header">
                                <h6>Column Visibility &amp; Order</h6>
                                <button class="btn-close" id="filter_close_${timestamp}" type="button"></button>
                            </div>

                            <div class="ledger_filter_search">
                                <input type="text" class="form-control form-control-sm" id="${searchId}" placeholder="Search columns..." />
                            </div>

                            <div class="ledger_filter_actions">
                                <button class="btn btn-sm btn-light" id="show_all_${timestamp}">
                                    <i class="fa fa-check-square-o"></i> Show All
                                </button>
                                <button class="btn btn-sm btn-light" id="hide_all_${timestamp}">
                                    <i class="fa fa-square-o"></i> Hide All
                                </button>
                                <button class="btn btn-sm btn-warning" id="reset_${timestamp}">
                                    <i class="fa fa-refresh"></i> Reset
                                </button>
                            </div>

                            <div class="ledger_filter_columns" id="columns_list_${timestamp}">
                                ${columnItems}
                            </div>

                            <div class="ledger_filter_footer">
                                <small><span id="visible_count_${timestamp}">${visibleCount}</span> of ${this._ledgerFilterColumns.length} columns visible</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const filterDiv = document.createElement('div');
        filterDiv.innerHTML = filterHTML;

        listTable.parentElement.insertBefore(filterDiv.firstElementChild, listTable);
        this._ledgerFilterElement = document.querySelector('.ledger_column_filter_bar');

        this.attachLedgerFilterEvents(filterId, dropdownId, searchId, timestamp);
    },

    attachLedgerFilterEvents(filterId, dropdownId, searchId, timestamp) {
        const filterBtn = document.getElementById(filterId);
        const dropdown = document.getElementById(dropdownId);
        const closeBtn = document.getElementById(`filter_close_${timestamp}`);
        const searchInput = document.getElementById(searchId);
        const showAllBtn = document.getElementById(`show_all_${timestamp}`);
        const hideAllBtn = document.getElementById(`hide_all_${timestamp}`);
        const resetBtn = document.getElementById(`reset_${timestamp}`);
        const columnsList = document.getElementById(`columns_list_${timestamp}`);

        if (!filterBtn || !dropdown) return;

        // Toggle dropdown
        filterBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
        });

        // Close dropdown
        closeBtn.addEventListener('click', () => {
            dropdown.style.display = 'none';
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!filterBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });

        // Search functionality
        searchInput.addEventListener('input', (e) => {
            const search = e.target.value.toLowerCase();
            document.querySelectorAll('.ledger_column_item').forEach(item => {
                const label = item.querySelector('label').textContent.toLowerCase();
                item.style.display = label.includes(search) ? '' : 'none';
            });
        });

        // Show All
        showAllBtn.addEventListener('click', () => {
            this._ledgerFilterColumns.forEach(col => col.visible = true);
            this.updateLedgerColumnUI(timestamp);
            this.applyLedgerColumnFilter();
        });

        // Hide All
        hideAllBtn.addEventListener('click', () => {
            this._ledgerFilterColumns.forEach(col => col.visible = false);
            this.updateLedgerColumnUI(timestamp);
            this.applyLedgerColumnFilter();
        });

        // Reset
        resetBtn.addEventListener('click', () => {
            localStorage.removeItem('ledger_column_preferences');
            this.loadLedgerColumnPreferences();
            this.updateLedgerColumnUI(timestamp);
            this.applyLedgerColumnFilter();
        });

        // Column toggle
        columnsList.addEventListener('change', (e) => {
            if (e.target.classList.contains('column_toggle')) {
                const item = e.target.closest('.ledger_column_item');
                const colName = item.getAttribute('data-column');
                const col = this._ledgerFilterColumns.find(c => c.name === colName);
                if (col) {
                    col.visible = e.target.checked;
                    this.saveLedgerColumnPreferences();
                    this.updateLedgerColumnUI(timestamp);
                    this.applyLedgerColumnFilter();
                    this.updateFilterInfo();
                }
            }
        });

        // Move up/down
        columnsList.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-move-up, .btn-move-down');
            if (!btn) return;

            const item = e.target.closest('.ledger_column_item');
            const currentIndex = parseInt(item.getAttribute('data-index'));

            if (btn.classList.contains('btn-move-up') && currentIndex > 0) {
                [this._ledgerFilterColumns[currentIndex], this._ledgerFilterColumns[currentIndex - 1]] =
                    [this._ledgerFilterColumns[currentIndex - 1], this._ledgerFilterColumns[currentIndex]];

                this._ledgerFilterColumns.forEach((col, idx) => col.order = idx + 1);
                this.saveLedgerColumnPreferences();
                this.injectLedgerColumnFilter();
            } else if (btn.classList.contains('btn-move-down') && currentIndex < this._ledgerFilterColumns.length - 1) {
                [this._ledgerFilterColumns[currentIndex], this._ledgerFilterColumns[currentIndex + 1]] =
                    [this._ledgerFilterColumns[currentIndex + 1], this._ledgerFilterColumns[currentIndex]];

                this._ledgerFilterColumns.forEach((col, idx) => col.order = idx + 1);
                this.saveLedgerColumnPreferences();
                this.injectLedgerColumnFilter();
            }
        });
    },

    updateLedgerColumnUI(timestamp) {
        const visibleCount = this._ledgerFilterColumns.filter(c => c.visible).length;
        const countSpan = document.getElementById(`visible_count_${timestamp}`);
        if (countSpan) {
            countSpan.textContent = visibleCount;
        }

        document.querySelectorAll('.ledger_column_item').forEach(item => {
            const colName = item.getAttribute('data-column');
            const col = this._ledgerFilterColumns.find(c => c.name === colName);
            if (col) {
                item.querySelector('.column_toggle').checked = col.visible;
            }
        });
    },

    updateFilterInfo() {
        const filterInfo = document.querySelector('.ledger_filter_info');
        if (filterInfo) {
            const visibleCount = this._ledgerFilterColumns.filter(c => c.visible).length;
            filterInfo.textContent = `${visibleCount}/${this._ledgerFilterColumns.length} columns visible`;
        }
    },

    applyLedgerColumnFilter() {
        setTimeout(() => {
            const table = document.querySelector('.o_list_table');
            if (!table) return;

            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');

            // Hide/show columns
            this._ledgerFilterColumns.forEach((col, idx) => {
                const colIndex = idx + 1; // +1 for checkbox column

                if (headers[colIndex]) {
                    headers[colIndex].style.display = col.visible ? '' : 'none';
                }

                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells[colIndex]) {
                        cells[colIndex].style.display = col.visible ? '' : 'none';
                    }
                });
            });
        }, 100);
    },
});