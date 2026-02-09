/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PurchaseHistoryDialog } from "./purchase_history_dialog";

export const purchaseHistoryService = {
    dependencies: ["orm", "dialog", "notification"],

    start(env, { orm, dialog, notification }) {
        console.log("Purchase History Service started");

        const keydownHandler = async (ev) => {
            // Check for Ctrl+F5
            if (ev.ctrlKey && ev.key === 'F5') {
                ev.preventDefault();
                ev.stopPropagation();

                try {
                    const activeElement = document.activeElement;
                    let productId = null;
                    let productName = null;
                    let lineId = null;

                    // Method 1: Try to get from the focused row
                    const dataRow = activeElement.closest('tr.o_data_row');
                    if (dataRow) {
                        lineId = dataRow.dataset.id;

                        if (lineId) {
                            try {
                                // Read the line data to get product_id
                                const lineData = await orm.read(
                                    'account.move.line',
                                    [parseInt(lineId)],
                                    ['product_id', 'display_type']
                                );

                                if (lineData && lineData[0]) {
                                    // Check if this is a product line (not section/note)
                                    if (lineData[0].display_type === 'product' || !lineData[0].display_type) {
                                        if (lineData[0].product_id) {
                                            productId = lineData[0].product_id[0];
                                            productName = lineData[0].product_id[1];
                                        }
                                    }
                                }
                            } catch (error) {
                                console.log("Error reading line data:", error);
                            }
                        }
                    }

                    // Method 2: Try to find from selected cells
                    if (!productId) {
                        const selectedCell = document.querySelector('.o_data_row.o_selected_row .o_data_cell[name="product_id"]');
                        if (selectedCell) {
                            const parentRow = selectedCell.closest('tr.o_data_row');
                            if (parentRow) {
                                lineId = parentRow.dataset.id;
                                if (lineId) {
                                    try {
                                        const lineData = await orm.read(
                                            'account.move.line',
                                            [parseInt(lineId)],
                                            ['product_id', 'display_type']
                                        );

                                        if (lineData && lineData[0]) {
                                            if (lineData[0].display_type === 'product' || !lineData[0].display_type) {
                                                if (lineData[0].product_id) {
                                                    productId = lineData[0].product_id[0];
                                                    productName = lineData[0].product_id[1];
                                                }
                                            }
                                        }
                                    } catch (error) {
                                        console.log("Error reading selected line:", error);
                                    }
                                }
                            }
                        }
                    }

                    if (!productId) {
                        notification.add(
                            "Please select a product line first. Click on any invoice line with a product.",
                            { type: "warning" }
                        );
                        return;
                    }

                    // Fetch purchase history
                    const purchaseHistory = await orm.call(
                        'account.move.line',
                        'get_product_purchase_history',
                        [productId]
                    );

                    // Show dialog
                    dialog.add(PurchaseHistoryDialog, {
                        productName: productName || "Product",
                        purchaseHistory: purchaseHistory,
                    });

                } catch (error) {
                    console.error("Purchase History Error:", error);
                    notification.add(
                        "Error loading purchase history: " + error.message,
                        { type: "danger" }
                    );
                }
            }
        };

        // Add event listener
        window.addEventListener('keydown', keydownHandler);
        console.log("Ctrl+F5 listener added for purchase history");

        // Return cleanup function
        return {
            dispose() {
                window.removeEventListener('keydown', keydownHandler);
                console.log("Purchase History Service disposed");
            }
        };
    },
};

// Register the service
registry.category("services").add("purchaseHistoryService", purchaseHistoryService);