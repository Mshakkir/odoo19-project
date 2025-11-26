/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReorderNotificationDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            notifications: [],
            warehouses: [],
            selectedWarehouse: false,
            loading: true,
            counts: { total: 0, below_min: 0, above_max: 0 },
            filterType: 'all', // 'all', 'below_min', 'above_max'
        });

        onWillStart(async () => {
            await this.loadWarehouses();
            await this.loadNotifications();
        });
    }

    async loadWarehouses() {
        const warehouses = await this.orm.searchRead(
            "stock.warehouse",
            [],
            ["id", "name"],
            { order: "name" }
        );
        this.state.warehouses = warehouses;
    }

    async loadNotifications() {
        this.state.loading = true;
        try {
            const notifications = await this.orm.call(
                "stock.warehouse.orderpoint",
                "get_reorder_notifications",
                [this.state.selectedWarehouse]
            );

            const counts = await this.orm.call(
                "stock.warehouse.orderpoint",
                "get_notification_count",
                [this.state.selectedWarehouse]
            );

            this.state.notifications = notifications;
            this.state.counts = counts;
        } catch (error) {
            console.error("Error loading notifications:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onWarehouseChange(ev) {
        this.state.selectedWarehouse = parseInt(ev.target.value) || false;
        await this.loadNotifications();
    }

    onFilterChange(filterType) {
        this.state.filterType = filterType;
    }

    get filteredNotifications() {
        if (this.state.filterType === 'all') {
            return this.state.notifications;
        }
        return this.state.notifications.filter(
            n => n.notification_type === this.state.filterType
        );
    }

    async openProduct(productId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.product",
            res_id: productId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openReorderRule(orderpointId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.warehouse.orderpoint",
            res_id: orderpointId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async refreshNotifications() {
        await this.loadNotifications();
    }

    getNotificationClass(type) {
        return type === 'below_min' ? 'alert-danger' : 'alert-warning';
    }

    getNotificationIcon(type) {
        return type === 'below_min' ? 'fa-arrow-down' : 'fa-arrow-up';
    }
}

ReorderNotificationDashboard.template = "warehouse_reorder_notification.Dashboard";

registry.category("actions").add("reorder_notification_dashboard", ReorderNotificationDashboard);
