/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useService } from "@web/core/utils/hooks";
import { PurchaseHistoryDialog } from "./purchase_history_dialog";

export class ProductPurchaseHistoryField extends Many2OneField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        // Add keyboard event listener
        window.addEventListener('keydown', this.onKeyDown.bind(this));
    }

    onWillUnmount() {
        super.onWillUnmount();
        window.removeEventListener('keydown', this.onKeyDown.bind(this));
    }

    async onKeyDown(ev) {
        // Check for Ctrl+F5
        if (ev.ctrlKey && ev.key === 'F5') {
            ev.preventDefault();
            ev.stopPropagation();
            await this.showPurchaseHistory();
        }
    }

    async showPurchaseHistory() {
        const productId = this.props.record.data[this.props.name] && this.props.record.data[this.props.name][0];
        const productName = this.props.record.data[this.props.name] && this.props.record.data[this.props.name][1];

        if (!productId) {
            this.notification.add(
                "Please select a product first",
                { type: "warning" }
            );
            return;
        }

        try {
            // Call the model method to get purchase history
            const purchaseHistory = await this.orm.call(
                'account.move.line',
                'get_product_purchase_history',
                [productId]
            );

            // Show dialog with purchase history
            this.dialog.add(PurchaseHistoryDialog, {
                productName: productName || "Unknown Product",
                purchaseHistory: purchaseHistory,
            });

        } catch (error) {
            this.notification.add(
                "Error loading purchase history: " + error.message,
                { type: "danger" }
            );
        }
    }
}

// Register the widget
registry.category("fields").add("product_purchase_history", ProductPurchaseHistoryField);