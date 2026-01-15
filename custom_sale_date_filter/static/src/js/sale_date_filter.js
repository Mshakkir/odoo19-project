/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class SaleDateFilterComponent extends Component {
    static template = "custom_sale_date_filter.DateFilterTemplate";
    static props = ["*"];

    setup() {
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
            this.env.services.notification.add(
                "Please select both start and end dates",
                { type: "warning" }
            );
            return;
        }

        const domain = [
            ['date_order', '>=', this.state.dateFrom + ' 00:00:00'],
            ['date_order', '<=', this.state.dateTo + ' 23:59:59']
        ];

        // Update the search model with the new domain
        this.env.searchModel.setDomainParts({
            date_filter: domain,
        });
    }

    clearFilter() {
        this.state.dateFrom = this.getDefaultDateFrom();
        this.state.dateTo = this.getDefaultDateTo();

        // Remove the date filter domain
        this.env.searchModel.setDomainParts({
            date_filter: [],
        });
    }
}

export class SaleOrderListController extends ListController {
    static components = {
        ...ListController.components,
        SaleDateFilterComponent,
    };

    static template = "custom_sale_date_filter.ListController";
}

export const saleOrderListView = {
    ...listView,
    Controller: SaleOrderListController,
};

registry.category("views").add("sale_order_list_with_date_filter", saleOrderListView);