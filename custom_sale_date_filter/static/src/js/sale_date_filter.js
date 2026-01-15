/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks";

class SaleDateFilter extends Component {
    static template = "custom_sale_date_filter.DateFilter";
    static props = {
        updateDomain: { type: Function },
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            dateFrom: this.getDefaultDateFrom(),
            dateTo: this.getDefaultDateTo(),
        });
    }

    getDefaultDateFrom() {
        const date = new Date();
        date.setDate(1);
        return date.toISOString().split('T')[0];
    }

    getDefaultDateTo() {
        const date = new Date();
        return date.toISOString().split('T')[0];
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
    }

    applyFilter() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            this.notification.add("Please select both start and end dates", {
                type: "warning",
            });
            return;
        }

        if (this.state.dateFrom > this.state.dateTo) {
            this.notification.add("Start date must be before end date", {
                type: "warning",
            });
            return;
        }

        const domain = [
            ['date_order', '>=', this.state.dateFrom + ' 00:00:00'],
            ['date_order', '<=', this.state.dateTo + ' 23:59:59']
        ];

        this.props.updateDomain(domain);

        this.notification.add("Date filter applied successfully", {
            type: "success",
        });
    }

    clearFilter() {
        this.state.dateFrom = this.getDefaultDateFrom();
        this.state.dateTo = this.getDefaultDateTo();
        this.props.updateDomain([]);

        this.notification.add("Filter cleared", {
            type: "info",
        });
    }
}

class SaleOrderListController extends ListController {
    static template = "custom_sale_date_filter.ListView";
    static components = {
        ...ListController.components,
        SaleDateFilter,
    };

    setup() {
        super.setup();
    }

    updateDomain(domain) {
        try {
            // Get current domain and remove any existing date_order filters
            let currentDomain = this.model.root.domain || [];

            // Filter out existing date_order conditions
            const cleanDomain = currentDomain.filter(item => {
                if (Array.isArray(item) && item.length > 0) {
                    return item[0] !== 'date_order';
                }
                return true;
            });

            // Add new domain
            const newDomain = [...cleanDomain, ...domain];

            // Update the model
            this.model.root.domain = newDomain;
            this.model.root.load();
        } catch (error) {
            console.error('Error updating domain:', error);
        }
    }
}

export const saleOrderListView = {
    ...listView,
    Controller: SaleOrderListController,
};

registry.category("views").add("sale_order_tree_date_filter", saleOrderListView);