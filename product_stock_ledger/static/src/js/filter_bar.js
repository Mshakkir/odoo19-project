/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

// ── Date helpers ──────────────────────────────────────────────────────────────
function autoFormat(raw) {
    const d = raw.replace(/\D/g, "").slice(0, 6);
    if (d.length <= 2) return d;
    if (d.length <= 4) return d.slice(0,2) + "/" + d.slice(2);
    return d.slice(0,2) + "/" + d.slice(2,4) + "/" + d.slice(4,6);
}

function isValidDisplay(val) {
    return /^\d{2}\/\d{2}\/\d{2}$/.test(val);
}

function displayToIso(val) {
    // "21/02/26" → "2026-02-21"
    const m = val.match(/^(\d{2})\/(\d{2})\/(\d{2})$/);
    if (!m) return "";
    return `20${m[3]}-${m[2]}-${m[1]}`;
}

function isoToDisplay(iso) {
    // "2026-02-21" → "21/02/26"
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return "";
    return `${m[3]}/${m[2]}/${m[1].slice(2)}`;
}

// ── Filter Bar Component ──────────────────────────────────────────────────────
class StockLedgerFilterBar extends Component {
    static template = "product_stock_ledger.FilterBar";
    static props = { model: Object };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            product: "",
            productId: null,
            warehouseId: "",
            dateFromDisplay: "",
            dateToDisplay: "",
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

    // ── Date text input (manual typing) ──────────────────────────────────────
    onDateFromInput(ev) {
        const fmt = autoFormat(ev.target.value);
        this.state.dateFromDisplay = fmt;
        ev.target.value = fmt;
        this.state.dateFrom = isValidDisplay(fmt) ? displayToIso(fmt) : "";
    }
    onDateFromBlur(ev) {
        if (ev.target.value && !isValidDisplay(ev.target.value)) {
            this.state.dateFromDisplay = "";
            this.state.dateFrom = "";
            ev.target.value = "";
        }
    }

    onDateToInput(ev) {
        const fmt = autoFormat(ev.target.value);
        this.state.dateToDisplay = fmt;
        ev.target.value = fmt;
        this.state.dateTo = isValidDisplay(fmt) ? displayToIso(fmt) : "";
    }
    onDateToBlur(ev) {
        if (ev.target.value && !isValidDisplay(ev.target.value)) {
            this.state.dateToDisplay = "";
            this.state.dateTo = "";
            ev.target.value = "";
        }
    }

    // ── Calendar icon clicked → trigger the hidden date input ────────────────
    openDateFrom(ev) {
        // Find the sibling hidden date input and click it
        const wrap = ev.currentTarget.closest(".slf-date-wrap");
        const picker = wrap.querySelector(".slf-date-hidden");
        if (picker) picker.showPicker ? picker.showPicker() : picker.click();
    }

    openDateTo(ev) {
        const wrap = ev.currentTarget.closest(".slf-date-wrap");
        const picker = wrap.querySelector(".slf-date-hidden");
        if (picker) picker.showPicker ? picker.showPicker() : picker.click();
    }

    // ── Calendar picker selected a date ──────────────────────────────────────
    onDateFromPicker(ev) {
        const iso = ev.target.value;  // "2026-02-21"
        this.state.dateFrom = iso;
        this.state.dateFromDisplay = isoToDisplay(iso);
    }

    onDateToPicker(ev) {
        const iso = ev.target.value;
        this.state.dateTo = iso;
        this.state.dateToDisplay = isoToDisplay(iso);
    }

    // ── Product autocomplete ──────────────────────────────────────────────────
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

    selectProduct(p) {
        this.state.product = p.display_name;
        this.state.productId = p.id;
        this.state.acVisible = false;
        this.state.acResults = [];
    }

    hideAc() { setTimeout(() => { this.state.acVisible = false; }, 180); }

    // ── Domain builder ────────────────────────────────────────────────────────
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
        // invoice_status is stored as human-readable title-case (e.g. "Invoiced",
        // "To Invoice", "Nothing"). Use "=" for exact match since the SQL view
        // now outputs consistent title-case labels.
        if (s.invoiceStatus) d.push(["invoice_status", "=", s.invoiceStatus]);
        return d;
    }

    async apply() {
        const domain = this._buildDomain();
        try {
            await this.props.model.load({ domain });
            this.props.model.notify();
        } catch (_) {
            try {
                await this.props.model.root.load({ domain });
                this.props.model.notify();
            } catch (e) { console.warn("[SLFilter] apply failed:", e); }
        }
    }

    async clear() {
        Object.assign(this.state, {
            product: "", productId: null, warehouseId: "",
            dateFromDisplay: "", dateToDisplay: "",
            dateFrom: "", dateTo: "", voucher: "",
            moveType: "", invoiceStatus: "",
            acVisible: false, acResults: [],
        });
        try {
            await this.props.model.load({ domain: [] });
            this.props.model.notify();
        } catch (_) {
            try {
                await this.props.model.root.load({ domain: [] });
                this.props.model.notify();
            } catch (e) { console.warn("[SLFilter] clear failed:", e); }
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

// ── Patch ListRenderer to declare StockLedgerFilterBar ────────────────────────
patch(ListRenderer, {
    components: {
        ...ListRenderer.components,
        StockLedgerFilterBar,
    },
});


















///** @odoo-module **/
//
//import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { patch } from "@web/core/utils/patch";
//import { ListRenderer } from "@web/views/list/list_renderer";
//
//// ── Date helpers ──────────────────────────────────────────────────────────────
//function autoFormat(raw) {
//    const d = raw.replace(/\D/g, "").slice(0, 6);
//    if (d.length <= 2) return d;
//    if (d.length <= 4) return d.slice(0,2) + "/" + d.slice(2);
//    return d.slice(0,2) + "/" + d.slice(2,4) + "/" + d.slice(4,6);
//}
//
//function isValidDisplay(val) {
//    return /^\d{2}\/\d{2}\/\d{2}$/.test(val);
//}
//
//function displayToIso(val) {
//    // "21/02/26" → "2026-02-21"
//    const m = val.match(/^(\d{2})\/(\d{2})\/(\d{2})$/);
//    if (!m) return "";
//    return `20${m[3]}-${m[2]}-${m[1]}`;
//}
//
//function isoToDisplay(iso) {
//    // "2026-02-21" → "21/02/26"
//    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
//    if (!m) return "";
//    return `${m[3]}/${m[2]}/${m[1].slice(2)}`;
//}
//
//// ── Filter Bar Component ──────────────────────────────────────────────────────
//class StockLedgerFilterBar extends Component {
//    static template = "product_stock_ledger.FilterBar";
//    static props = { model: Object };
//
//    setup() {
//        this.orm = useService("orm");
//        this.state = useState({
//            product: "",
//            productId: null,
//            warehouseId: "",
//            dateFromDisplay: "",
//            dateToDisplay: "",
//            dateFrom: "",
//            dateTo: "",
//            voucher: "",
//            moveType: "",
//            invoiceStatus: "",
//            warehouses: [],
//            acResults: [],
//            acVisible: false,
//        });
//        this._acTimer = null;
//        this._boundKey = this._onKey.bind(this);
//        onMounted(() => {
//            document.addEventListener("keydown", this._boundKey);
//            this._loadWarehouses();
//        });
//        onWillUnmount(() => {
//            document.removeEventListener("keydown", this._boundKey);
//        });
//    }
//
//    async _loadWarehouses() {
//        try {
//            const rows = await this.orm.searchRead(
//                "stock.warehouse", [], ["id", "name"], { limit: 200 }
//            );
//            this.state.warehouses = rows;
//        } catch (_) {}
//    }
//
//    // ── Date text input (manual typing) ──────────────────────────────────────
//    onDateFromInput(ev) {
//        const fmt = autoFormat(ev.target.value);
//        this.state.dateFromDisplay = fmt;
//        ev.target.value = fmt;
//        this.state.dateFrom = isValidDisplay(fmt) ? displayToIso(fmt) : "";
//    }
//    onDateFromBlur(ev) {
//        if (ev.target.value && !isValidDisplay(ev.target.value)) {
//            this.state.dateFromDisplay = "";
//            this.state.dateFrom = "";
//            ev.target.value = "";
//        }
//    }
//
//    onDateToInput(ev) {
//        const fmt = autoFormat(ev.target.value);
//        this.state.dateToDisplay = fmt;
//        ev.target.value = fmt;
//        this.state.dateTo = isValidDisplay(fmt) ? displayToIso(fmt) : "";
//    }
//    onDateToBlur(ev) {
//        if (ev.target.value && !isValidDisplay(ev.target.value)) {
//            this.state.dateToDisplay = "";
//            this.state.dateTo = "";
//            ev.target.value = "";
//        }
//    }
//
//    // ── Calendar icon clicked → trigger the hidden date input ────────────────
//    openDateFrom(ev) {
//        // Find the sibling hidden date input and click it
//        const wrap = ev.currentTarget.closest(".slf-date-wrap");
//        const picker = wrap.querySelector(".slf-date-hidden");
//        if (picker) picker.showPicker ? picker.showPicker() : picker.click();
//    }
//
//    openDateTo(ev) {
//        const wrap = ev.currentTarget.closest(".slf-date-wrap");
//        const picker = wrap.querySelector(".slf-date-hidden");
//        if (picker) picker.showPicker ? picker.showPicker() : picker.click();
//    }
//
//    // ── Calendar picker selected a date ──────────────────────────────────────
//    onDateFromPicker(ev) {
//        const iso = ev.target.value;  // "2026-02-21"
//        this.state.dateFrom = iso;
//        this.state.dateFromDisplay = isoToDisplay(iso);
//    }
//
//    onDateToPicker(ev) {
//        const iso = ev.target.value;
//        this.state.dateTo = iso;
//        this.state.dateToDisplay = isoToDisplay(iso);
//    }
//
//    // ── Product autocomplete ──────────────────────────────────────────────────
//    onProductInput(ev) {
//        const q = ev.target.value;
//        this.state.product = q;
//        this.state.productId = null;
//        clearTimeout(this._acTimer);
//        if (!q.trim()) {
//            this.state.acResults = [];
//            this.state.acVisible = false;
//            return;
//        }
//        this._acTimer = setTimeout(async () => {
//            try {
//                const res = await this.orm.searchRead(
//                    "product.product",
//                    ["|", ["name","ilike",q], ["default_code","ilike",q]],
//                    ["id","display_name","default_code"],
//                    { limit: 20, order: "default_code asc, name asc" }
//                );
//                this.state.acResults = res;
//                this.state.acVisible = res.length > 0;
//            } catch (_) {}
//        }, 280);
//    }
//
//    selectProduct(p) {
//        this.state.product = p.display_name;
//        this.state.productId = p.id;
//        this.state.acVisible = false;
//        this.state.acResults = [];
//    }
//
//    hideAc() { setTimeout(() => { this.state.acVisible = false; }, 180); }
//
//    // ── Domain builder ────────────────────────────────────────────────────────
//    _buildDomain() {
//        const s = this.state;
//        const d = [];
//        if (s.productId)     d.push(["product_id", "=", s.productId]);
//        else if (s.product)  d.push(["product_id.display_name", "ilike", s.product]);
//        if (s.warehouseId)   d.push(["warehouse_id", "=", parseInt(s.warehouseId)]);
//        if (s.dateFrom)      d.push(["date", ">=", s.dateFrom + " 00:00:00"]);
//        if (s.dateTo)        d.push(["date", "<=", s.dateTo   + " 23:59:59"]);
//        if (s.voucher)       d.push(["voucher", "ilike", s.voucher]);
//        if (s.moveType)      d.push(["move_type", "=", s.moveType]);
//        if (s.invoiceStatus) d.push(["invoice_status", "=", s.invoiceStatus]);
//        return d;
//    }
//
//    async apply() {
//        const domain = this._buildDomain();
//        try {
//            await this.props.model.load({ domain });
//            this.props.model.notify();
//        } catch (_) {
//            try {
//                await this.props.model.root.load({ domain });
//                this.props.model.notify();
//            } catch (e) { console.warn("[SLFilter] apply failed:", e); }
//        }
//    }
//
//    async clear() {
//        Object.assign(this.state, {
//            product: "", productId: null, warehouseId: "",
//            dateFromDisplay: "", dateToDisplay: "",
//            dateFrom: "", dateTo: "", voucher: "",
//            moveType: "", invoiceStatus: "",
//            acVisible: false, acResults: [],
//        });
//        try {
//            await this.props.model.load({ domain: [] });
//            this.props.model.notify();
//        } catch (_) {
//            try {
//                await this.props.model.root.load({ domain: [] });
//                this.props.model.notify();
//            } catch (e) { console.warn("[SLFilter] clear failed:", e); }
//        }
//    }
//
//    _onKey(ev) {
//        if (document.querySelector(".o_dialog, .modal.show")) return;
//        const active = document.activeElement;
//        const barEl  = this.__owl__?.bdom?.el;
//        const inBar  = barEl && barEl.contains(active);
//        if (!inBar) {
//            const tag = active?.tagName;
//            if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
//        }
//        if (ev.key === "Enter")  { ev.preventDefault(); this.apply(); }
//        if (ev.key === "Escape") { ev.preventDefault(); this.clear(); }
//    }
//}
//
//// ── Patch ListRenderer to declare StockLedgerFilterBar ────────────────────────
//patch(ListRenderer, {
//    components: {
//        ...ListRenderer.components,
//        StockLedgerFilterBar,
//    },
//});
//
//
