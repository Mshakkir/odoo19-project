/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StockMonitorDialog } from "./stock_monitor_dialog";

export const stockMonitorService = {
    dependencies: ["orm", "dialog", "notification"],

    start(env, { orm, dialog, notification }) {
        console.log("Stock Monitor Service Started");

        const keydownHandler = async (ev) => {
            // Check for Ctrl+F7
            if (ev.ctrlKey && ev.key === 'F7') {
                ev.preventDefault();
                ev.stopPropagation();

                try {
                    console.log("Ctrl+F7 pressed");

                    let productId = null;
                    let productName = null;

                    // Find all product many2one fields
                    const productFields = document.querySelectorAll('[name="product_id"]');

                    console.log("Found", productFields.length, "product fields");

                    // Try to find a selected/focused product field
                    for (const field of productFields) {
                        const row = field.closest('tr.o_data_row');
                        const isActive = row && (
                            row.classList.contains('o_selected_row') ||
                            row.contains(document.activeElement) ||
                            field.contains(document.activeElement)
                        );

                        if (isActive || !productId) {
                            // Method 1: Get product from link (readonly records)
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

                            // Method 2: Get from input (edit mode)
                            if (!productId || !isActive) {
                                const input = field.querySelector('input.o_input');
                                if (input && input.value && input.value.trim()) {
                                    productName = input.value.trim();
                                    console.log("Found product name from input:", productName);

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

                    // Method 3: Last attempt if we have name but no ID
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
                        console.log("No product found");
                        notification.add(
                            "Please select a product first. Click on the Product field, select a product, then press Ctrl+F7.",
                            {
                                type: "warning",
                                title: "No Product Selected",
                                sticky: false
                            }
                        );
                        return;
                    }

                    console.log("Fetching stock monitor for product ID:", productId, "Name:", productName);

                    // Fetch stock data
                    let stockData;
                    try {
                        stockData = await orm.call(
                            'product.product',
                            'get_product_stock_monitor',
                            [productId]
                        );
                        console.log("✓ Stock monitor call successful");
                        console.log("  Warehouses returned:", stockData ? stockData.length : 0);
                        console.log("  Data:", stockData);
                    } catch (stockError) {
                        console.error("✗ Error fetching stock monitor:", stockError);
                        notification.add(
                            "Error fetching stock data: " + stockError.message,
                            {
                                type: "danger",
                                title: "Error"
                            }
                        );
                        return;
                    }

                    if (!stockData || stockData.length === 0) {
                        console.log("No warehouses found");
                        notification.add(
                            `No warehouse data found for ${productName}`,
                            {
                                type: "info",
                                title: "No Data",
                                sticky: false
                            }
                        );
                        return;
                    }

                    // Show dialog
                    console.log("Attempting to show stock monitor dialog...");
                    try {
                        dialog.add(StockMonitorDialog, {
                            productName: productName || "Product",
                            stockData: stockData,
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
                    console.error("Stock Monitor Error:", error);
                    console.error("Error stack:", error.stack);
                    notification.add(
                        "Error loading stock monitor: " + error.message,
                        {
                            type: "danger",
                            title: "Error"
                        }
                    );
                }
            }
        };

        // Use capture phase to catch the event
        window.addEventListener('keydown', keydownHandler, true);
        console.log("Ctrl+F7 listener registered");

        return {
            dispose() {
                window.removeEventListener('keydown', keydownHandler, true);
                console.log("Stock Monitor Service disposed");
            }
        };
    },
};

// Register the service
registry.category("services").add("stockMonitorService", stockMonitorService);