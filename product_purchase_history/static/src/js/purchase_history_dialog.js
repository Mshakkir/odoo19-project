///** @odoo-module **/
//
//import { Component } from "@odoo/owl";
//import { Dialog } from "@web/core/dialog/dialog";
//import { _t } from "@web/core/l10n/translation";
//
//export class PurchaseHistoryDialog extends Component {
//    static template = "product_purchase_history.PurchaseHistoryDialog";
//    static components = { Dialog };
//    static props = {
//        close: Function,
//        productName: String,
//        purchaseHistory: Array,
//    };
//
//    get hasHistory() {
//        return this.props.purchaseHistory && this.props.purchaseHistory.length > 0;
//    }
//
//    get title() {
//        return _t("Purchase History - ") + this.props.productName;
//    }
//
//    formatNumber(value, decimals = 2) {
//        if (value === null || value === undefined) return '0.00';
//        return parseFloat(value).toFixed(decimals);
//    }
//
//    getStateLabel(state) {
//        const stateLabels = {
//            'purchase': _t('Purchase Order'),
//            'done': _t('Done'),
//        };
//        return stateLabels[state] || state;
//    }
//}
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class PurchaseHistoryDialog extends Component {
    static template = "product_purchase_history.PurchaseHistoryDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        purchaseHistory: Array,
    };

    get hasHistory() {
        return this.props.purchaseHistory?.length > 0;
    }

    get title() {
        return _t("Purchase History - ") + this.props.productName;
    }

    formatNumber(value, decimals = 2) {
        return value ? parseFloat(value).toFixed(decimals) : '0.00';
    }

    getSourceLabel(source) {
        return source === 'PO'
            ? _t('Purchase Order')
            : _t('Vendor Bill');
    }
}
