/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

patch(ListController.prototype, {
    setup() {
        super.setup();

        // Only initialize for invoice views
        if (this.props.resModel === 'account.move') {
            this.dateFrom = '';
            this.dateTo = '';
        }
    },

    /**
     * Apply date filter to the list
     */
    async applyDateFilter() {
        if (this.props.resModel !== 'account.move') return;

        try {
            // Validate dates
            if (this.dateFrom && this.dateTo && this.dateFrom > this.dateTo) {
                this.notification.add(
                    'From Date cannot be after To Date',
                    { type: 'warning' }
                );
                return;
            }

            // Build domain based on entered dates
            let domain = [];

            if (this.dateFrom && this.dateTo) {
                domain = [
                    '&',
                    ['invoice_date', '>=', this.dateFrom],
                    ['invoice_date', '<=', this.dateTo]
                ];
            } else if (this.dateFrom) {
                domain = [['invoice_date', '>=', this.dateFrom]];
            } else if (this.dateTo) {
                domain = [['invoice_date', '<=', this.dateTo]];
            }

            // Apply the filter
            if (domain.length > 0) {
                await this.model.load({ domain });
            } else {
                await this.model.load();
            }

        } catch (error) {
            console.error('[Invoice Date Filter] Error applying filter:', error);
            if (this.notification) {
                this.notification.add(
                    'Error applying date filter. Please try again.',
                    { type: 'danger' }
                );
            }
        }
    },

    /**
     * Handle From Date change
     */
    onDateFromChange(ev) {
        this.dateFrom = ev.target.value;
        if (ev.type === 'change') {
            this.applyDateFilter();
        }
    },

    /**
     * Handle To Date change
     */
    onDateToChange(ev) {
        this.dateTo = ev.target.value;
        if (ev.type === 'change') {
            this.applyDateFilter();
        }
    },

    /**
     * Clear date filters
     */
    async clearDateFilters() {
        this.dateFrom = '';
        this.dateTo = '';
        await this.model.load();
    }
});

console.log('[Invoice Date Filter] Module loaded successfully');