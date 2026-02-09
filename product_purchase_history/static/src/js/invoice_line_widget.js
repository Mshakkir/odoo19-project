/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { PurchaseHistoryDialog } from "./purchase_history_dialog";
import { useService } from "@web/core/utils/hooks";

// Extend the Many2One field for product_id
export class ProductMany2OneWithHistory extends Many2OneField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        // Listen for Ctrl+F5 when this field is focused
        this.addKeyListener();
    }

    addKeyListener() {
        const handleKeyDown = async (ev) => {
            if (ev.ctrlKey && ev.key === 'F5') {
                ev.preventDefault();
                ev.stopPropagation();
                await this.showPurchaseHistory();
            }
        };

        // Store the handler so we can remove it later
        this.keyHandler = handleKeyDown;
    }

    async showPurchaseHistory() {
        try {
            console.log("Showing purchase history, current value:", this.props.record.data[this.props.name]);

            const productValue = this.props.record.data[this.props.name];
            let productId = null;
            let productName = null;

            // Handle different formats of Many2One value
            if (Array.isArray(productValue) && productValue.length >= 2) {
                productId = productValue[0];
                productName = productValue[1];
            } else if (productValue && typeof productValue === 'object') {
                productId = productValue.id;
                productName = productValue.display_name || productValue.name;
            } else if (typeof productValue === 'number') {
                productId = productValue;
            }

            if (!productId) {
                this.notification.add(
                    "Please select a product first",
                    { type: "warning", title: "No Product Selected" }
                );
                return;
            }

            console.log("Fetching history for product:", productId, productName);

            // Fetch purchase history
            const purchaseHistory = await this.orm.call(
                'account.move.line',
                'get_product_purchase_history',
                [productId]
            );

            console.log("Purchase history:", purchaseHistory);

            if (!purchaseHistory || purchaseHistory.length === 0) {
                this.notification.add(
                    `No purchase history found for ${productName || 'this product'}`,
                    { type: "info", title: "No History" }
                );
                return;
            }

            // Show dialog
            this.dialog.add(PurchaseHistoryDialog, {
                productName: productName || `Product ${productId}`,
                purchaseHistory: purchaseHistory,
            });

        } catch (error) {
            console.error("Error showing purchase history:", error);
            this.notification.add(
                "Error loading purchase history: " + error.message,
                { type: "danger", title: "Error" }
            );
        }
    }
}

// Register this field specifically for product_id in account.move.line
registry.category("fields").add("product_many2one_with_history", ProductMany2OneWithHistory);


// Also add a global service as backup
export const purchaseHistoryService = {
    dependencies: ["orm", "dialog", "notification"],

    start(env, { orm, dialog, notification }) {
        console.log("Purchase History Global Service started");

        const keydownHandler = async (ev) => {
            if (ev.ctrlKey && ev.key === 'F5') {
                ev.preventDefault();
                ev.stopPropagation();

                try {
                    console.log("Ctrl+F5 pressed globally");

                    // Find all product many2one fields that are currently visible
                    const productFields = document.querySelectorAll('[name="product_id"]');

                    let productId = null;
                    let productName = null;

                    // First, try to find a selected/focused product field
                    for (const field of productFields) {
                        // Check if this field or its row is selected
                        const row = field.closest('tr.o_data_row');
                        const isActive = row && (
                            row.classList.contains('o_selected_row') ||
                            row.contains(document.activeElement)
                        );

                        if (isActive || field.contains(document.activeElement)) {
                            // Try to get product from link
                            const link = field.querySelector('a[data-tooltip]');
                            if (link) {
                                try {
                                    const tooltip = JSON.parse(link.getAttribute('data-tooltip'));
                                    if (tooltip.id) {
                                        productId = tooltip.id;
                                        productName = link.textContent.trim();
                                        console.log("Found product from active field:", productId, productName);
                                        break;
                                    }
                                } catch (e) {}
                            }

                            // Try to get from input value
                            const input = field.querySelector('input');
                            if (input && input.value && !productId) {
                                productName = input.value;
                                console.log("Found product name from input:", productName);
                            }
                        }
                    }

                    // If we only have the name, search for the product
                    if (!productId && productName) {
                        console.log("Searching for product by name:", productName);
                        const products = await orm.call(
                            'product.product',
                            'name_search',
                            [productName, [], 'ilike', 1]
                        );

                        if (products && products.length > 0) {
                            productId = products[0][0];
                            productName = products[0][1];
                            console.log("Found product by search:", productId, productName);
                        }
                    }

                    if (!productId) {
                        // Last resort: look for any visible product
                        for (const field of productFields) {
                            const link = field.querySelector('a[data-tooltip]');
                            if (link) {
                                try {
                                    const tooltip = JSON.parse(link.getAttribute('data-tooltip'));
                                    if (tooltip.id) {
                                        productId = tooltip.id;
                                        productName = link.textContent.trim();
                                        console.log("Using first visible product:", productId, productName);
                                        break;
                                    }
                                } catch (e) {}
                            }
                        }
                    }

                    if (!productId) {
                        notification.add(
                            "Please select a product in the invoice line first. After selecting from the dropdown, click on the row and press Ctrl+F5.",
                            { type: "warning", title: "No Product Selected" }
                        );
                        return;
                    }

                    console.log("Fetching purchase history for:", productId, productName);

                    const purchaseHistory = await orm.call(
                        'account.move.line',
                        'get_product_purchase_history',
                        [productId]
                    );

                    console.log("Purchase history:", purchaseHistory);

                    if (!purchaseHistory || purchaseHistory.length === 0) {
                        notification.add(
                            `No purchase history found for ${productName}`,
                            { type: "info", title: "No History" }
                        );
                        return;
                    }

                    dialog.add(PurchaseHistoryDialog, {
                        productName: productName || "Product",
                        purchaseHistory: purchaseHistory,
                    });

                } catch (error) {
                    console.error("Purchase History Error:", error);
                    notification.add(
                        "Error: " + error.message,
                        { type: "danger" }
                    );
                }
            }
        };

        window.addEventListener('keydown', keydownHandler, true);
        console.log("Ctrl+F5 listener registered");

        return {
            dispose() {
                window.removeEventListener('keydown', keydownHandler, true);
            }
        };
    },
};

registry.category("services").add("purchaseHistoryService", purchaseHistoryService);