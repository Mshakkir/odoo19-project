/** @odoo-module **/

/**
 * Hide the built-in company currency conversion row (1,875.00 SR)
 * from the tax_totals widget on Purchase Order forms.
 *
 * We use a MutationObserver to watch for the widget rendering
 * and hide the currency row after it renders, since the widget
 * is rendered by JavaScript after page load.
 */

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

function hidePOCurrencyRow(el) {
    if (!el) return;
    // Find all tax total tables inside purchase order form
    const form = el.closest?.(".o_purchase_order") || el.querySelector?.(".o_purchase_order");
    if (!form) return;

    // The currency conversion row is the last tr inside the tax totals table
    // It contains the company currency amount like (1,875.00 SR)
    const taxTotalsField = form.querySelector("[name='tax_totals']");
    if (!taxTotalsField) return;

    // Target rows containing currency conversion data
    // Odoo renders these as rows with class containing 'currency' or as the last row
    const rows = taxTotalsField.querySelectorAll("tr");
    rows.forEach((row) => {
        const text = row.textContent || "";
        // Hide rows that contain SAR symbol or company currency symbol
        // The built-in row shows values like "(1,875.00 ﷼)" or "1,875.00 SR"
        if (
            row.classList.contains("o_tax_total_currency") ||
            row.classList.contains("o_currency_row") ||
            row.dataset?.currencyConversion ||
            (text.includes("﷼") && !row.closest(".o_field_monetary[name='amount_total_company_currency']"))
        ) {
            row.style.display = "none";
        }
    });

    // Also hide any standalone div/span with currency conversion
    const currencyDivs = taxTotalsField.querySelectorAll(
        ".o_currency_conversion, .o_tax_currency_conversion, [class*='currency_conversion']"
    );
    currencyDivs.forEach((el) => (el.style.display = "none"));
}

// Patch FormController to run hide logic after each render on purchase.order
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (this.props.resModel === "purchase.order") {
                hidePOCurrencyRow(this.__owl__.bdom?.el || document.querySelector(".o_purchase_order"));
            }
        });
        onPatched(() => {
            if (this.props.resModel === "purchase.order") {
                hidePOCurrencyRow(this.__owl__.bdom?.el || document.querySelector(".o_purchase_order"));
            }
        });
    },
});