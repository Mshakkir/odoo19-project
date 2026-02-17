import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class StockLocationDialog extends Component {
    static template = "product_stock_locations.StockLocationDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productName: String,
        stockLocations: Array,
    };

    get hasStock() {
        return this.props.stockLocations && this.props.stockLocations.length > 0;
    }

    get title() {
        return _t("Stock Availability - ") + this.props.productName;
    }

    formatNumber(value, decimals = 2) {
        if (value === null || value === undefined) return '0.00';
        return parseFloat(value).toFixed(decimals);
    }

    isTotal(record) {
        return record.id === -1;
    }

    getAvailableClass(available) {
        if (available <= 0) return 'text-danger fw-bold';
        if (available < 5) return 'text-warning fw-bold';
        return 'text-success fw-bold';
    }
}