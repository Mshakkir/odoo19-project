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

                    console.log("Ctrl+F5 pressed, searching for product...");

                    // Try to find the active record in the list/form view
                    const listController = document.querySelector('.o_list_view');
                    const formController = document.querySelector('.o_form_view');

                    if (listController || formController) {
                        // Find the selected/active row
                        let dataRow = activeElement.closest('tr.o_data_row');

                        if (!dataRow) {
                            dataRow = document.querySelector('tr.o_data_row.o_selected_row');
                        }

                        if (!dataRow) {
                            dataRow = document.querySelector('tr.o_data_row.o_row_edit');
                        }

                        if (dataRow) {
                            console.log("Found row, searching for product field...");

                            // Method 1: Try to get product from the many2one field widget
                            const productCell = dataRow.querySelector('[name="product_id"]');
                            if (productCell) {
                                // Check if there's an anchor tag with the product info
                                const productLink = productCell.querySelector('a[data-tooltip]');
                                if (productLink) {
                                    const tooltipData = productLink.getAttribute('data-tooltip');
                                    if (tooltipData) {
                                        try {
                                            const tooltip = JSON.parse(tooltipData);
                                            if (tooltip.id) {
                                                productId = tooltip.id;
                                                productName = productLink.textContent.trim();
                                                console.log("Got product from tooltip:", productId, productName);
                                            }
                                        } catch (e) {
                                            console.log("Error parsing tooltip:", e);
                                        }
                                    }
                                }

                                // Method 2: Try to get from input field
                                if (!productId) {
                                    const productInput = productCell.querySelector('input');
                                    if (productInput) {
                                        // Try to access the component data
                                        const fieldWidget = productInput.closest('.o_field_widget');
                                        if (fieldWidget && fieldWidget.__owl__) {
                                            const component = fieldWidget.__owl__.component;
                                            if (component && component.props && component.props.record) {
                                                const recordData = component.props.record.data;
                                                if (recordData.product_id) {
                                                    if (Array.isArray(recordData.product_id)) {
                                                        productId = recordData.product_id[0];
                                                        productName = recordData.product_id[1];
                                                    } else if (typeof recordData.product_id === 'object' && recordData.product_id.id) {
                                                        productId = recordData.product_id.id;
                                                        productName = recordData.product_id.display_name;
                                                    }
                                                    console.log("Got product from component:", productId, productName);
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Method 3: Try to access the record data from the row element
                            if (!productId && dataRow.__owl__) {
                                const rowComponent = dataRow.__owl__.component;
                                if (rowComponent && rowComponent.props && rowComponent.props.record) {
                                    const recordData = rowComponent.props.record.data;
                                    console.log("Record data from row component:", recordData);
                                    if (recordData.product_id) {
                                        if (Array.isArray(recordData.product_id)) {
                                            productId = recordData.product_id[0];
                                            productName = recordData.product_id[1];
                                        } else if (typeof recordData.product_id === 'object' && recordData.product_id.id) {
                                            productId = recordData.product_id.id;
                                            productName = recordData.product_id.display_name;
                                        }
                                        console.log("Got product from row component:", productId, productName);
                                    }
                                }
                            }

                            // Method 4: If still no product, try reading from database (for saved records only)
                            if (!productId && dataRow.dataset.id) {
                                const lineId = dataRow.dataset.id;
                                // Only try to read if it's not a virtual ID
                                if (!lineId.startsWith('datapoint_') && !lineId.startsWith('virtual_')) {
                                    try {
                                        console.log("Trying to read from database, ID:", lineId);
                                        const lineData = await orm.read(
                                            'account.move.line',
                                            [parseInt(lineId)],
                                            ['product_id', 'display_type']
                                        );

                                        if (lineData && lineData[0]) {
                                            console.log("Line data from DB:", lineData[0]);
                                            if ((lineData[0].display_type === 'product' || !lineData[0].display_type)
                                                && lineData[0].product_id) {
                                                productId = lineData[0].product_id[0];
                                                productName = lineData[0].product_id[1];
                                                console.log("Got product from database:", productId, productName);
                                            }
                                        }
                                    } catch (error) {
                                        console.log("Error reading from database:", error);
                                    }
                                }
                            }
                        }
                    }

                    if (!productId) {
                        console.log("No product found");
                        notification.add(
                            "Please select a product in the line first, then click on the row (not in the dropdown) and press Ctrl+F5",
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