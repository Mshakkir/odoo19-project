/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks";

export class SaleDateFilter extends Component {
    static template = "custom_sale_date_filter.DateFilter";

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

        const domain = [
            ['date_order', '>=', this.state.dateFrom + ' 00:00:00'],
            ['date_order', '<=', this.state.dateTo + ' 23:59:59']
        ];

        this.props.updateDomain(domain);
    }

    clearFilter() {
        this.state.dateFrom = this.getDefaultDateFrom();
        this.state.dateTo = this.getDefaultDateTo();
        this.props.updateDomain([]);
    }
}

export class SaleOrderListController extends ListController {
    setup() {
        super.setup();
    }

    updateDomain(domain) {
        this.model.root.domain = domain;
        this.model.root.load();
    }
}

SaleOrderListController.template = "custom_sale_date_filter.ListView";
SaleOrderListController.components = {
    ...ListController.components,
    SaleDateFilter,
};

export const saleOrderListView = {
    ...listView,
    Controller: SaleOrderListController,
};

registry.category("views").add("sale_order_date_filter_list", saleOrderListView);