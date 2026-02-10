import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class StockMonitorDialog extends Component {
    static template = "product_stock_monitor.StockMonitorDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        stockData: Array,
    };

    get hasStock() {
        return this.props.stockData && this.props.stockData.length > 0;
    }

    get title() {
        return _t("Stock Monitor - ") + this.props.productName;
    }

    formatNumber(value, decimals = 2) {
        if (value === null || value === undefined) return '0.00';
        return parseFloat(value).toFixed(decimals);
    }

    getTotalQty() {
        if (!this.hasStock) return 0;
        return this.props.stockData.reduce((sum, item) => sum + (item.qty || 0), 0);
    }
}