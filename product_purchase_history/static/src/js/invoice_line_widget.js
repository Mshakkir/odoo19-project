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

                    console.log("Ctrl+F5 pressed, searching for product...");

                    // Method 1: Try to get from many2one input field directly
                    const many2oneInput = activeElement.closest('.o_field_many2one');
                    if (many2oneInput) {
                        console.log("Found many2one field");
                        const input = many2oneInput.querySelector('input');
                        if (input) {
                            // Try to get from data attributes
                            const recordData = input.getAttribute('data-oe-id');
                            if (recordData) {
                                productId = parseInt(recordData);
                                productName = input.value;
                                console.log("Got product from input data attribute:", productId, productName);
                            }

                            // Alternative: try to get from the autocomplete widget
                            if (!productId && input.value) {
                                productName = input.value;
                                // We have the name, try to find the row to get the ID
                                const parentRow = input.closest('tr.o_data_row');
                                if (parentRow && parentRow.dataset.id) {
                                    lineId = parentRow.dataset.id;
                                }
                            }
                        }
                    }

                    // Method 2: Try to get from the currently focused/edited row
                    if (!lineId) {
                        let dataRow = activeElement.closest('tr.o_data_row');

                        // Method 3: If not in a row, try to find the selected row
                        if (!dataRow) {
                            dataRow = document.querySelector('tr.o_data_row.o_selected_row');
                        }

                        // Method 4: Try to find any row being edited
                        if (!dataRow) {
                            dataRow = document.querySelector('tr.o_data_row.o_row_edit');
                        }

                        // Method 5: Look for the row containing the active element
                        if (!dataRow && activeElement) {
                            dataRow = activeElement.closest('tr[data-id]');
                        }

                        if (dataRow && dataRow.dataset.id) {
                            lineId = dataRow.dataset.id;
                            console.log("Found row ID:", lineId);
                        }
                    }

                    // If we found a line ID, read the product from the database
                    if (lineId && !productId) {
                        try {
                            console.log("Reading line data from database...");
                            const lineData = await orm.read(
                                'account.move.line',
                                [parseInt(lineId)],
                                ['product_id', 'display_type']
                            );

                            if (lineData && lineData[0]) {
                                console.log("Line data:", lineData[0]);
                                // Check if this is a product line (not section/note)
                                if (lineData[0].display_type === 'product' || !lineData[0].display_type) {
                                    if (lineData[0].product_id) {
                                        productId = lineData[0].product_id[0];
                                        productName = lineData[0].product_id[1];
                                        console.log("Got product from database:", productId, productName);
                                    }
                                } else {
                                    console.log("This is a section/note line, not a product");
                                }
                            }
                        } catch (error) {
                            console.log("Error reading line data:", error);
                        }
                    }

                    if (!productId) {
                        console.log("No product found");
                        notification.add(
                            "Please click on a product line first (click on the row, not inside the dropdown), then press Ctrl+F5",
                            { type: "warning" }
                        );
                        return;
                    }

                    console.log("Fetching purchase history for product:", productId);

                    // Fetch purchase history
                    const purchaseHistory = await orm.call(
                        'account.move.line',
                        'get_product_purchase_history',
                        [productId]
                    );

                    console.log("Purchase history:", purchaseHistory);

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