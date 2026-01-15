/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

class SaleDateFilter extends Component {
    static template = "custom_sale_date_filter.DateFilter";
    static props = {};

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");

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

        // Reload with new domain using action service
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sale Orders',
            res_model: 'sale.order',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
        });

        this.notification.add("Date filter applied successfully", {
            type: "success",
        });
    }

    clearFilter() {
        this.state.dateFrom = this.getDefaultDateFrom();
        this.state.dateTo = this.getDefaultDateTo();

        // Reload without date filter
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sale Orders',
            res_model: 'sale.order',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });

        this.notification.add("Filter cleared", {
            type: "info",
        });
    }
}

class SaleOrderListRenderer extends ListRenderer {
    static template = "custom_sale_date_filter.ListRenderer";
    static components = {
        ...ListRenderer.components,
        SaleDateFilter,
    };
}

export const saleOrderListView = {
    ...listView,
    Renderer: SaleOrderListRenderer,
};

// Register specifically for sale.order model
registry.category("views").add("sale_order_tree_date_filter", saleOrderListView);