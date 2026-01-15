/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

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

// Patch ListController to inject date filter
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            // Only for sale.order model
            if (this.props.resModel === 'sale.order') {
                this.injectDateFilter();
            }
        });
    },

    injectDateFilter() {
        // Find the list renderer element
        const listView = document.querySelector('.o_list_view');

        if (listView && !document.querySelector('.sale_date_filter_container')) {
            // Create filter container
            const filterDiv = document.createElement('div');
            filterDiv.className = 'sale_date_filter_wrapper_main';

            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const dateFrom = firstDay.toISOString().split('T')[0];
            const dateTo = today.toISOString().split('T')[0];

            filterDiv.innerHTML = `
                <div class="sale_date_filter_container">
                    <div class="date_filter_wrapper">
                        <label class="date_label">Order Date:</label>

                        <div class="date_input_group">
                            <input
                                type="date"
                                class="form-control date_input"
                                id="date_from_input"
                                value="${dateFrom}"
                            />

                            <span class="date_separator">→</span>

                            <input
                                type="date"
                                class="form-control date_input"
                                id="date_to_input"
                                value="${dateTo}"
                            />
                        </div>

                        <button class="btn btn-primary apply_filter_btn" id="apply_date_filter">
                            Apply Filter
                        </button>

                        <button class="btn btn-secondary clear_filter_btn" id="clear_date_filter">
                            Clear
                        </button>
                    </div>
                </div>
            `;

            // Insert before the list view
            listView.parentElement.insertBefore(filterDiv, listView);

            // Add event listeners
            const applyBtn = document.getElementById('apply_date_filter');
            const clearBtn = document.getElementById('clear_date_filter');
            const dateFromInput = document.getElementById('date_from_input');
            const dateToInput = document.getElementById('date_to_input');

            applyBtn.addEventListener('click', () => {
                const dateFrom = dateFromInput.value;
                const dateTo = dateToInput.value;

                if (!dateFrom || !dateTo) {
                    this.notification.add("Please select both dates", { type: "warning" });
                    return;
                }

                if (dateFrom > dateTo) {
                    this.notification.add("Start date must be before end date", { type: "warning" });
                    return;
                }

                const domain = [
                    ['date_order', '>=', dateFrom + ' 00:00:00'],
                    ['date_order', '<=', dateTo + ' 23:59:59']
                ];

                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Sale Orders',
                    res_model: 'sale.order',
                    views: [[false, 'list'], [false, 'form']],
                    domain: domain,
                    target: 'current',
                });

                this.notification.add("Date filter applied", { type: "success" });
            });

            clearBtn.addEventListener('click', () => {
                const today = new Date();
                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                dateFromInput.value = firstDay.toISOString().split('T')[0];
                dateToInput.value = today.toISOString().split('T')[0];

                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Sale Orders',
                    res_model: 'sale.order',
                    views: [[false, 'list'], [false, 'form']],
                    target: 'current',
                });

                this.notification.add("Filter cleared", { type: "info" });
            });
        }
    },
});