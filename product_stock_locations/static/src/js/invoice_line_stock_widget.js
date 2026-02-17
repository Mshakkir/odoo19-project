/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StockLocationDialog } from "./stock_location_dialog";

export const stockLocationService = {
    dependencies: ["orm", "dialog", "notification"],

    start(env, { orm, dialog, notification }) {
        console.log("Stock Location Service Started");

        const keydownHandler = async (ev) => {
            // Check for Ctrl+F9
            if (ev.ctrlKey && ev.key === 'F9') {
                ev.preventDefault();
                ev.stopPropagation();

                try {
                    console.log("Ctrl+F9 pressed");

                    let productId = null;
                    let productName = null;

                    // Find all product many2one fields that are currently visible
                    const productFields = document.querySelectorAll('[name="product_id"]');

                    console.log("Found", productFields.length, "product fields");

                    // First, try to find a selected/focused product field
                    for (const field of productFields) {
                        const row = field.closest('tr.o_data_row');
                        const isActive = row && (
                            row.classList.contains('o_selected_row') ||
                            row.contains(document.activeElement) ||
                            field.contains(document.activeElement)
                        );

                        if (isActive || !productId) {
                            // Method 1: Try to get product from link (readonly/saved records)
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

                            // Method 2: Try to get from input value (edit mode)
                            if (!productId || !isActive) {
                                const input = field.querySelector('input.o_input');
                                if (input && input.value && input.value.trim()) {
                                    productName = input.value.trim();
                                    console.log("Found product name from input:", productName);

                                    if (isActive && productName) {
                                        try {
                                            const products = await orm.call(
                                                'product.product',
                                                'name_search',
                                                [productName, [], 'ilike', 5]
                                            );

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

                    // Method 3: Last attempt search by name
                    if (!productId && productName) {
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
                            "Please select a product first. Click on the Product field, select a product from the dropdown, then press Ctrl+F9.",
                            {
                                type: "warning",
                                title: "No Product Selected",
                                sticky: false
                            }
                        );
                        return;
                    }

                    console.log("Fetching stock locations for product ID:", productId, "Name:", productName);

                    // Fetch stock locations
                    let stockLocations;
                    try {
                        stockLocations = await orm.call(
                            'account.move.line',
                            'get_product_stock_locations',
                            [productId]
                        );
                        console.log("✓ Stock locations call successful");
                        console.log("  Records returned:", stockLocations ? stockLocations.length : 0);
                    } catch (stockError) {
                        console.error("✗ Error fetching stock locations:", stockError);
                        notification.add(
                            "Error fetching stock data: " + stockError.message,
                            {
                                type: "danger",
                                title: "Error"
                            }
                        );
                        return;
                    }

                    if (!stockLocations || stockLocations.length === 0) {
                        notification.add(
                            `No stock found for ${productName} in any location.`,
                            {
                                type: "info",
                                title: "No Stock",
                                sticky: false
                            }
                        );
                        return;
                    }

                    // Show dialog
                    try {
                        dialog.add(StockLocationDialog, {
                            productName: productName || "Product",
                            stockLocations: stockLocations,
                        });
                        console.log("✓ Stock Location Dialog opened successfully");
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
                    console.error("Stock Location Error:", error);
                    notification.add(
                        "Error loading stock data: " + error.message,
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
        console.log("Ctrl+F9 listener registered (capture phase)");

        return {
            dispose() {
                window.removeEventListener('keydown', keydownHandler, true);
                console.log("Stock Location Service disposed");
            }
        };
    },
};

// Register the service
registry.category("services").add("stockLocationService", stockLocationService);