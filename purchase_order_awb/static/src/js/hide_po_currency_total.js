/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountTaxTotalsField } from "@account/components/account_tax_totals/account_tax_totals";

/**
 * Patch the AccountTaxTotalsField widget to hide the company currency
 * conversion row on the Purchase Order form.
 * We replace it with our own manual-rate field (amount_total_company_currency).
 */
patch(AccountTaxTotalsField.prototype, {
    /**
     * Override to suppress company currency display when the record
     * is a purchase.order and a manual rate field is present.
     */
    get hasCurrencyConversion() {
        // Check if we are in purchase order context
        const model = this.props.record?.model?.config?.resModel;
        if (model === "purchase.order") {
            return false; // Hide the built-in currency conversion row
        }
        return super.hasCurrencyConversion;
    },
});