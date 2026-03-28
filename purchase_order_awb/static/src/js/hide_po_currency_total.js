/** @odoo-module **/

/**
 * Hide the built-in company currency conversion row from tax_totals widget
 * on Purchase Order form using direct DOM manipulation via MutationObserver.
 *
 * The tax_totals widget renders a table. The company currency row
 * in Odoo 19 is rendered inside the OWL component as a <tr> with
 * class "o_tax_totals_line" containing the company currency amount.
 * We use MutationObserver to catch it after OWL renders it.
 */

function hideCompanyCurrencyRow() {
    // Only act on purchase order pages
    const form = document.querySelector(".o_purchase_order");
    if (!form) return;

    const taxTotalsEl = form.querySelector("[name='tax_totals']");
    if (!taxTotalsEl) return;

    // Get all table rows in the tax totals widget
    const allRows = taxTotalsEl.querySelectorAll("tr, .o_tax_totals_line");
    allRows.forEach((row) => {
        const text = row.innerText || row.textContent || "";
        // The built-in company currency row shows bracketed amount like (1,875.00 ﷼)
        // Match rows that ONLY contain a bracketed amount (company currency conversion)
        if (/^\s*\([\d,\s.]+\s*[^\)]*\)\s*$/.test(text.trim())) {
            row.style.cssText = "display: none !important;";
        }
    });

    // Also try direct class-based hiding for known Odoo 19 classes
    const knownClasses = [
        ".o_tax_totals_foreign_currency",
        ".o_tax_total_company_currency",
        "[class*='company_currency']",
        "[class*='foreign_currency']",
        "[class*='currency_conversion']",
    ];
    knownClasses.forEach((selector) => {
        taxTotalsEl.querySelectorAll(selector).forEach((el) => {
            el.style.cssText = "display: none !important;";
        });
    });
}

// Run on initial page load
document.addEventListener("DOMContentLoaded", () => {
    // Use MutationObserver to catch OWL re-renders
    const observer = new MutationObserver(() => {
        hideCompanyCurrencyRow();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    // Also run immediately in case already rendered
    hideCompanyCurrencyRow();
});

// Also run after Owl component updates via a periodic check
// (fallback for cases where MutationObserver misses the update)
let checkCount = 0;
const interval = setInterval(() => {
    hideCompanyCurrencyRow();
    checkCount++;
    if (checkCount > 20) clearInterval(interval); // Stop after 20 attempts
}, 500);