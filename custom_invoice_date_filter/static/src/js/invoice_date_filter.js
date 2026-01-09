/** @odoo-module **/

/**
 * Safe Invoice Date Filter Module for Odoo 19 CE
 *
 * This module safely extends the ListController to add date filters
 * Error handling ensures it won't break the UI if something goes wrong
 */

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useState, onWillStart, onMounted } from "@odoo/owl";

// Safe patch with error handling
try {
    patch(ListController.prototype, {
        /**
         * Setup method - initializes the date filter state
         */
        setup() {
            try {
                // Call parent setup first (CRITICAL for safety)
                super.setup();

                // Only initialize if we're in an invoice view
                if (this.props.resModel === 'account.move') {
                    // Initialize date filter state
                    this.dateFilterState = useState({
                        dateFrom: '',
                        dateTo: '',
                        isFiltering: false
                    });
                }
            } catch (error) {
                // If setup fails, call parent and log error
                console.error('[Invoice Date Filter] Setup error:', error);
                super.setup();
            }
        },

        /**
         * Apply date filter to the list
         */
        async applyDateFilter() {
            // Safety check: only proceed if we have the state
            if (!this.dateFilterState) {
                console.warn('[Invoice Date Filter] State not initialized');
                return;
            }

            try {
                const dateFrom = this.dateFilterState.dateFrom;
                const dateTo = this.dateFilterState.dateTo;

                // Validate dates
                if (dateFrom && dateTo && dateFrom > dateTo) {
                    this.notification.add(
                        'From Date cannot be after To Date',
                        { type: 'warning' }
                    );
                    return;
                }

                this.dateFilterState.isFiltering = true;

                // Build domain based on entered dates
                let domain = [];

                if (dateFrom && dateTo) {
                    // Both dates entered - range filter
                    domain = [
                        '&',
                        ['invoice_date', '>=', dateFrom],
                        ['invoice_date', '<=', dateTo]
                    ];
                } else if (dateFrom) {
                    // Only from date - filter from date onwards
                    domain = [['invoice_date', '>=', dateFrom]];
                } else if (dateTo) {
                    // Only to date - filter up to date
                    domain = [['invoice_date', '<=', dateTo]];
                }

                // Apply the filter by reloading with new domain
                if (this.model && this.model.root) {
                    await this.model.root.load({
                        domain: domain,
                    });
                }

                this.dateFilterState.isFiltering = false;

            } catch (error) {
                console.error('[Invoice Date Filter] Error applying filter:', error);
                this.dateFilterState.isFiltering = false;

                // Show user-friendly error message
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
            if (!this.dateFilterState) return;

            try {
                this.dateFilterState.dateFrom = ev.target.value;

                // Apply filter on Enter key or change event
                if (ev.type === 'change' || ev.key === 'Enter') {
                    this.applyDateFilter();
                }
            } catch (error) {
                console.error('[Invoice Date Filter] Error in onDateFromChange:', error);
            }
        },

        /**
         * Handle To Date change
         */
        onDateToChange(ev) {
            if (!this.dateFilterState) return;

            try {
                this.dateFilterState.dateTo = ev.target.value;

                // Apply filter on Enter key or change event
                if (ev.type === 'change' || ev.key === 'Enter') {
                    this.applyDateFilter();
                }
            } catch (error) {
                console.error('[Invoice Date Filter] Error in onDateToChange:', error);
            }
        },

        /**
         * Clear date filters
         */
        async clearDateFilters() {
            if (!this.dateFilterState) return;

            try {
                this.dateFilterState.dateFrom = '';
                this.dateFilterState.dateTo = '';

                // Reload without domain filter
                if (this.model && this.model.root) {
                    await this.model.root.load({
                        domain: [],
                    });
                }
            } catch (error) {
                console.error('[Invoice Date Filter] Error clearing filters:', error);
            }
        }
    });

    console.log('[Invoice Date Filter] Module loaded successfully');

} catch (error) {
    // Critical error - log it but don't break Odoo
    console.error('[Invoice Date Filter] CRITICAL - Failed to patch ListController:', error);
    console.warn('[Invoice Date Filter] Module disabled due to error. Uninstall the module to remove this warning.');
}