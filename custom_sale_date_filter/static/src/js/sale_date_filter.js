/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SaleDateFilter extends Component {
    static template = "custom_sale_date_filter.SaleDateFilter";

    setup() {
        this.state = useState({
            dateFrom: this.getDefaultDateFrom(),
            dateTo: this.getDefaultDateTo(),
        });
        this.action = useService("action");
    }

    getDefaultDateFrom() {
        const date = new Date();
        date.setDate(1);
        return date.toISOString().split('T')[0];
    }

    getDefaultDateTo() {
        const date = new Date();
        date.setMonth(date.getMonth() + 1, 0);
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
    }
}

registry.category("actions").add("sale_date_filter_action", SaleDateFilter);