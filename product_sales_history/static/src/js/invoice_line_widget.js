/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SalesHistoryDialog } from "./sales_history_dialog";

export const salesHistoryService = {
    dependencies: ["orm", "dialog", "notification"],

    start(env, { orm, dialog, notification }) {
        console.log("Sales History Service Started - Diagnostic Version");

        const keydownHandler = async (ev) => {
            // Check for Ctrl+F6
            if (ev.ctrlKey && ev.key === 'F6') {
                ev.preventDefault();
                ev.stopPropagation();

                try {
                    console.log("Ctrl+F6 pressed");

                    let productId = null;
                    let productName = null;

                    // Find all product many2one fields that are currently visible
                    const productFields = document.querySelectorAll('[name="product_id"]');

                    console.log("Found", productFields.length, "product fields");

                    // First, try to find a selected/focused product field
                    for (const field of productFields) {
                        // Check if this field or its row is selected
                        const row = field.closest('tr.o_data_row');
                        const isActive = row && (
                            row.classList.contains('o_selected_row') ||
                            row.contains(document.activeElement) ||
                            field.contains(document.activeElement)
                        );

                        if (isActive || !productId) {
                            // Method 1: Try to get product from link (for saved/readonly records)
                            const link = field.querySelector('a[data-tooltip]');
                            if (link) {
                                try {
                                    const tooltip = JSON.parse(link.getAttribute('data-tooltip'));
                                    if (tooltip.id) {
                                        productId = tooltip.id;
                                        productName = link.textContent.trim();
                                        console.log("Found product from link:", productId, productName);
                                        if (isActive) break;
                                    }
                                } catch (e) {
                                    console.log("Error parsing tooltip:", e);
                                }
                            }

                            // Method 2: Try to get from input value (for edit mode)
                            if (!productId || !isActive) {
                                const input = field.querySelector('input.o_input');
                                if (input && input.value && input.value.trim()) {
                                    productName = input.value.trim();
                                    console.log("Found product name from input:", productName);

                                    // If this is the active row and we have a name, search for it
                                    if (isActive && productName) {
                                        console.log("Searching for product by name:", productName);
                                        try {
                                            const products = await orm.call(
                                                'product.product',
                                                'name_search',
                                                [productName, [], 'ilike', 5]
                                            );

                                            console.log("Search results:", products);

                                            if (products && products.length > 0) {
                                                // Use exact match if available, otherwise first result
                                                let matchedProduct = products[0];
                                                for (const product of products) {
                                                    if (product[1].toLowerCase() === productName.toLowerCase()) {
                                                        matchedProduct = product;
                                                        break;
                                                    }
                                                }
                                                productId = matchedProduct[0];
                                                productName = matchedProduct[1];
                                                console.log("Found product by search:", productId, productName);
                                                break;
                                            }
                                        } catch (searchError) {
                                            console.error("Product search error:", searchError);
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Method 3: If still no product but we have a name from somewhere, search
                    if (!productId && productName) {
                        console.log("Last attempt - searching for:", productName);
                        try {
                            const products = await orm.call(
                                'product.product',
                                'name_search',
                                [productName, [], 'ilike', 1]
                            );

                            if (products && products.length > 0) {
                                productId = products[0][0];
                                productName = products[0][1];
                                console.log("Found product in last attempt:", productId, productName);
                            }
                        } catch (searchError) {
                            console.error("Final search error:", searchError);
                        }
                    }

                    if (!productId) {
                        console.log("No product found after all attempts");
                        notification.add(
                            "Please select a product first. Click on the Product field, select a product from the dropdown, then press Ctrl+F6.",
                            {
                                type: "warning",
                                title: "No Product Selected",
                                sticky: false
                            }
                        );
                        return;
                    }

                    console.log("Fetching sales history for product ID:", productId, "Name:", productName);

                    // Fetch sales history
                    let salesHistory;
                    try {
                        salesHistory = await orm.call(
                            'account.move.line',
                            'get_product_sales_history',
                            [productId]
                        );
                        console.log("✓ Sales history call successful");
                        console.log("  Records returned:", salesHistory ? salesHistory.length : 0);
                        console.log("  Data:", salesHistory);
                    } catch (historyError) {
                        console.error("✗ Error fetching sales history:", historyError);
                        notification.add(
                            "Error fetching sales history: " + historyError.message,
                            {
                                type: "danger",
                                title: "Error"
                            }
                        );
                        return;
                    }

                    if (!salesHistory || salesHistory.length === 0) {
                        console.log("No sales history found");
                        notification.add(
                            `No sales history found for ${productName}`,
                            {
                                type: "info",
                                title: "No History",
                                sticky: false
                            }
                        );
                        return;
                    }

                    // Show dialog
                    console.log("Attempting to show dialog...");
                    try {
                        dialog.add(SalesHistoryDialog, {
                            productName: productName || "Product",
                            salesHistory: salesHistory,
                        });
                        console.log("✓ Dialog opened successfully");
                    } catch (dialogError) {
                        console.error("✗ Error opening dialog:", dialogError);
                        notification.add(
                            "Error displaying dialog: " + dialogError.message,
                            {
                                type: "danger",
                                title: "Dialog Error"
                            }
                        );
                    }

                } catch (error) {
                    console.error("Sales History Error:", error);
                    console.error("Error stack:", error.stack);
                    notification.add(
                        "Error loading sales history: " + error.message,
                        {
                            type: "danger",
                            title: "Error"
                        }
                    );
                }
            }
        };

        // Use capture phase to ensure we catch the event
        window.addEventListener('keydown', keydownHandler, true);
        console.log("Ctrl+F6 listener registered (capture phase)");

        return {
            dispose() {
                window.removeEventListener('keydown', keydownHandler, true);
                console.log("Sales History Service disposed");
            }
        };
    },
};

// Register the service
registry.category("services").add("salesHistoryService", salesHistoryService);