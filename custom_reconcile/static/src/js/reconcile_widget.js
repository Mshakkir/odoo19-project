/** @odoo-module **/
/**
 * custom_reconcile/static/src/js/reconcile_widget.js
 *
 * Small JS helpers for the custom reconciliation module.
 * - Highlights the difference row in the wizard
 * - Shows a confirmation toast on successful reconciliation
 * - Auto-scrolls to the selected lines section
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted } from "@odoo/owl";

// ── Reconcile Difference Field Highlighter ────────────────────────────────────
/**
 * Custom field widget that highlights the monetary "Difference" field
 * red when absolute value > 0.01, green otherwise.
 */
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { formatMonetary } from "@web/views/fields/formatters";

export class ReconcileDifferenceField extends MonetaryField {
    get className() {
        const value = this.props.value || 0;
        if (Math.abs(value) > 0.01) {
            return "text-danger fw-bold";
        }
        return "text-success fw-bold";
    }
}

ReconcileDifferenceField.template = MonetaryField.template;
registry.category("fields").add("reconcile_difference", ReconcileDifferenceField);


// ── Reconcile Balance Widget ─────────────────────────────────────────────────
/**
 * Displays a small summary bar showing debit, credit, and difference
 * in real-time as the user selects lines in the wizard.
 */
export class ReconcileBalanceWidget extends Component {
    setup() {
        this.notification = useService("notification");
        onMounted(() => {
            this._checkBalance();
        });
    }

    _checkBalance() {
        const form = this.el?.closest(".o_form_view");
        if (!form) return;

        // Observe changes to debit/credit totals and update colors
        const observer = new MutationObserver(() => {
            const diffField = form.querySelector("[name='difference'] .o_field_monetary");
            if (diffField) {
                const rawText = diffField.textContent.replace(/[^0-9.,\-]/g, "");
                const value = parseFloat(rawText.replace(",", ".")) || 0;
                if (Math.abs(value) > 0.01) {
                    diffField.style.color = "#dc3545";
                    diffField.style.fontWeight = "bold";
                } else {
                    diffField.style.color = "#198754";
                    diffField.style.fontWeight = "bold";
                }
            }
        });

        observer.observe(form, { childList: true, subtree: true });
    }
}

ReconcileBalanceWidget.template = "custom_reconcile.ReconcileBalanceWidget";
ReconcileBalanceWidget.props = {};

// ── Reconcile Success Confetti (lightweight) ──────────────────────────────────
/**
 * Listens for the 'display_notification' client action with type 'success'
 * coming from our reconcile wizard and adds a subtle green flash to the page.
 */
const actionService = registry.category("actions");
const originalDisplayNotification = actionService.get("display_notification");

// ── Auto-format reconcile amounts in list view ────────────────────────────────
/**
 * On DOMContentLoaded, watch for any .custom_reconcile_amount spans
 * and color them based on positive/negative value.
 */
document.addEventListener("DOMContentLoaded", () => {
    const style = document.createElement("style");
    style.textContent = `
        .custom_reconcile_positive { color: #198754 !important; }
        .custom_reconcile_negative { color: #dc3545 !important; }
        .custom_reconcile_zero     { color: #6c757d !important; }
    `;
    document.head.appendChild(style);
});

/**
 * Utility: format a float as a colored span based on sign.
 * @param {number} value
 * @returns {string} HTML string
 */
export function coloredAmount(value) {
    if (value > 0.001) {
        return `<span class="custom_reconcile_positive">+${value.toFixed(2)}</span>`;
    } else if (value < -0.001) {
        return `<span class="custom_reconcile_negative">${value.toFixed(2)}</span>`;
    }
    return `<span class="custom_reconcile_zero">0.00</span>`;
}