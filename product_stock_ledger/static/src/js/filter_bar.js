/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

class StockLedgerFilterBar extends Component {
    static template = "product_stock_ledger.FilterBar";
    static props = { model: Object };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            product: "",
            productId: null,
            warehouseId: "",
            dateFrom: "",
            dateTo: "",
            voucher: "",
            moveType: "",
            invoiceStatus: "",
            warehouses: [],
            acResults: [],
            acVisible: false,
        });
        this._acTimer = null;
        this._boundKey = this._onKey.bind(this);
        onMounted(() => {
            document.addEventListener("keydown", this._boundKey);
            this._loadWarehouses();
        });
        onWillUnmount(() => {
            document.removeEventListener("keydown", this._boundKey);
        });
    }

    async _loadWarehouses() {
        try {
            const rows = await this.orm.searchRead(
                "stock.warehouse", [], ["id", "name"], { limit: 200 }
            );
            this.state.warehouses = rows;
        } catch (_) {}
    }

    onProductInput(ev) {
        const q = ev.target.value;
        this.state.product = q;
        this.state.productId = null;
        clearTimeout(this._acTimer);
        if (!q.trim()) {
            this.state.acResults = [];
            this.state.acVisible = false;
            return;
        }
        this._acTimer = setTimeout(async () => {
            try {
                const res = await this.orm.searchRead(
                    "product.product",
                    ["|", ["name","ilike",q], ["default_code","ilike",q]],
                    ["id","display_name","default_code"],
                    { limit: 20, order: "default_code asc, name asc" }
                );
                this.state.acResults = res;
                this.state.acVisible = res.length > 0;
            } catch (_) {}
        }, 280);
    }

    // ✅ Fix 1: bound method instead of arrow in template
    selectProduct(p) {
        this.state.product = p.display_name;
        this.state.productId = p.id;
        this.state.acVisible = false;
        this.state.acResults = [];
    }

    hideAc() {
        setTimeout(() => { this.state.acVisible = false; }, 180);
    }

    _buildDomain() {
        const s = this.state;
        const d = [];
        if (s.productId)     d.push(["product_id", "=", s.productId]);
        else if (s.product)  d.push(["product_id.display_name", "ilike", s.product]);
        if (s.warehouseId)   d.push(["warehouse_id", "=", parseInt(s.warehouseId)]);
        if (s.dateFrom)      d.push(["date", ">=", s.dateFrom + " 00:00:00"]);
        if (s.dateTo)        d.push(["date", "<=", s.dateTo   + " 23:59:59"]);
        if (s.voucher)       d.push(["voucher", "ilike", s.voucher]);
        if (s.moveType)      d.push(["move_type", "=", s.moveType]);
        if (s.invoiceStatus) d.push(["invoice_status", "=", s.invoiceStatus]);
        return d;
    }

    // ✅ Fix 2: use model.load({domain}) instead of setting model.root.domain directly
    async apply() {
        const domain = this._buildDomain();
        try {
            await this.props.model.load({ domain });
            this.props.model.notify();
        } catch (e) {
            // fallback: try root.load
            try {
                await this.props.model.root.load({ domain });
                this.props.model.notify();
            } catch (e2) {
                console.warn("[SLFilter] apply failed:", e2);
            }
        }
    }

    async clear() {
        Object.assign(this.state, {
            product: "", productId: null, warehouseId: "",
            dateFrom: "", dateTo: "", voucher: "",
            moveType: "", invoiceStatus: "",
            acVisible: false, acResults: [],
        });
        try {
            await this.props.model.load({ domain: [] });
            this.props.model.notify();
        } catch (e) {
            try {
                await this.props.model.root.load({ domain: [] });
                this.props.model.notify();
            } catch (e2) {
                console.warn("[SLFilter] clear failed:", e2);
            }
        }
    }

    _onKey(ev) {
        if (document.querySelector(".o_dialog, .modal.show")) return;
        const active = document.activeElement;
        const barEl  = this.__owl__?.bdom?.el;
        const inBar  = barEl && barEl.contains(active);
        if (!inBar) {
            const tag = active?.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        }
        if (ev.key === "Enter")  { ev.preventDefault(); this.apply(); }
        if (ev.key === "Escape") { ev.preventDefault(); this.clear(); }
    }
}

// ✅ Patch ListRenderer.components so OWL template can find the component
patch(ListRenderer, {
    components: {
        ...ListRenderer.components,
        StockLedgerFilterBar,
    },
});
