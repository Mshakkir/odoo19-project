/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

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

// Patch ListRenderer to add the date filter component
patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.SaleDateFilterComponent = SaleDateFilter;
    },

    get isSaleOrderModel() {
        return this.props.list && this.props.list.resModel === 'sale.order';
    }
});