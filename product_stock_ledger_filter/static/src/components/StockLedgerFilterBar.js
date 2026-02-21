/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// ── Build domain from filter state ───────────────────────────────────────────
function buildDomain(f) {
    const d = [];
    if (f.product)       d.push(["product_id.display_name", "ilike", f.product]);
    if (f.warehouse)     d.push(["warehouse_id", "=", Number(f.warehouse)]);
    if (f.dateFrom)      d.push(["date", ">=", f.dateFrom + " 00:00:00"]);
    if (f.dateTo)        d.push(["date", "<=", f.dateTo   + " 23:59:59"]);
    if (f.voucher)       d.push(["voucher", "ilike", f.voucher]);
    if (f.moveType)      d.push(["move_type", "=", f.moveType]);
    if (f.invoiceStatus) d.push(["invoice_status", "=", f.invoiceStatus]);
    return d;
}

// ── OWL Filter Bar Component ──────────────────────────────────────────────────
export class StockLedgerFilterBar extends Component {
    static template = "product_stock_ledger_filter.FilterBar";
    static props = {
        onApply: Function,
        onClear: Function,
        warehouses: Array,
    };

    setup() {
        this.state = useState({
            product: "",
            warehouse: "",
            dateFrom: "",
            dateTo: "",
            voucher: "",
            moveType: "",
            invoiceStatus: "",
        });

        this._onKey = (ev) => {
            if (document.querySelector(".modal.show, .o_dialog")) return;
            if (ev.key === "Enter")  this.apply();
            if (ev.key === "Escape") this.clear();
        };

        onMounted(()      => document.addEventListener("keydown", this._onKey));
        onWillUnmount(() => document.removeEventListener("keydown", this._onKey));
    }

    apply() {
        this.props.onApply(buildDomain(this.state));
    }

    clear() {
        const s = this.state;
        s.product = ""; s.warehouse = ""; s.dateFrom = "";
        s.dateTo  = ""; s.voucher   = ""; s.moveType = "";
        s.invoiceStatus = "";
        this.props.onClear();
    }
}

// ── Register component so template can reference it ───────────────────────────
registry.category("owl_components").add("StockLedgerFilterBar", StockLedgerFilterBar);

// ── Patch ListController ──────────────────────────────────────────────────────
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.model?.config?.resModel !== "product.stock.ledger") return;

        this.orm = useService("orm");
        this.slWarehouses = useState({ list: [] });
        this._loadWarehouses();
    },

    async _loadWarehouses() {
        try {
            const rows = await this.orm.searchRead(
                "stock.warehouse", [], ["id", "name"], { limit: 200 }
            );
            this.slWarehouses.list = rows;
        } catch (_) {
            this.slWarehouses.list = [];
        }
    },

    onSLFilterApply(domain) {
        this.model.root.domain = domain;
        this.model.root.load().then(() => this.model.notify());
    },

    onSLFilterClear() {
        this.model.root.domain = [];
        this.model.root.load().then(() => this.model.notify());
    },
});
