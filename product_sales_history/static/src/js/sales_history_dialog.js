import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SalesHistoryDialog extends Component {
    static template = "product_sales_history.SalesHistoryDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        salesHistory: Array,
    };

    get hasHistory() {
        return this.props.salesHistory && this.props.salesHistory.length > 0;
    }

    get title() {
        return _t("Sales History - ") + this.props.productName;
    }

    formatNumber(value, decimals = 2) {
        if (value === null || value === undefined) return '0.00';
        return parseFloat(value).toFixed(decimals);
    }

    getStateLabel(state) {
        const stateLabels = {
            'draft': _t('Draft'),
            'posted': _t('Posted'),
        };
        return stateLabels[state] || state;
    }
}