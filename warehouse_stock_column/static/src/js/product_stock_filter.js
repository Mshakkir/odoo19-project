/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { Component, useState, useRef, onMounted, onWillUnmount, xml } from "@odoo/owl";

// ─────────────────────────────────────────────────────────────────────────────
//  ProductStockFilterBar — OWL Component
// ─────────────────────────────────────────────────────────────────────────────
class ProductStockFilterBar extends Component {
    static props = {
        onApply: Function,
        onClear: Function,
    };

    static template = xml`
        <div class="o_stock_filter_bar d-flex align-items-center flex-wrap gap-2 px-3 py-2 bg-white border-bottom">

            <div class="d-flex align-items-center gap-2">
                <select class="form-select form-select-sm" style="min-width:160px"
                    t-on-change="(ev) => state.stockType = ev.target.value">
                    <option value="">Stock</option>
                    <option value="zero"
                        t-att-selected="state.stockType === 'zero'">Zero Stock</option>
                    <option value="negative"
                        t-att-selected="state.stockType === 'negative'">Negative Stock</option>
                </select>
            </div>

            <div class="vr" style="height:24px"/>

            <div class="d-flex align-items-center gap-2">
                <span class="text-muted small fw-semibold text-nowrap">Greater Stock</span>
                <input
                    t-ref="gtInput"
                    type="text"
                    inputmode="decimal"
                    class="form-control form-control-sm"
                    placeholder="e.g. 10"
                    t-att-value="state.greaterThan"
                    t-on-input="onGtInput"
                    style="width:90px"
                />
            </div>

            <div class="vr" style="height:24px"/>

            <button class="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                t-on-click="applyFilters" title="Apply [Enter]">
                <i class="fa fa-filter"/><span>Apply</span>
            </button>
            <button class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                t-on-click="clearFilters" title="Clear [Esc]">
                <i class="fa fa-times"/><span>Clear</span>
            </button>

        </div>
    `;

    setup() {
        this.state = useState({ stockType: "", greaterThan: "" });
        this.gtInput = useRef("gtInput");

        this._handleKey = (ev) => {
            const active = document.activeElement;
            const inOurInput = this.gtInput.el && active === this.gtInput.el;

            if (ev.key === "Enter") {
                // Apply when Enter pressed in our input, or when no text-input is focused
                if (inOurInput || !active || active.tagName === "BODY") {
                    ev.preventDefault();
                    this.applyFilters();
                }
            }
            if (ev.key === "Escape") {
                this.clearFilters();
            }
        };

        onMounted(() => document.addEventListener("keydown", this._handleKey));
        onWillUnmount(() => document.removeEventListener("keydown", this._handleKey));
    }

    onGtInput(ev) {
        const v = ev.target.value;
        if (/^-?\d*\.?\d*$/.test(v)) {
            this.state.greaterThan = v;
        } else {
            ev.target.value = this.state.greaterThan;
        }
    }

    applyFilters() {
        const domain = [];
        if (this.state.stockType === "zero") {
            domain.push(["qty_available", "=", 0]);
        } else if (this.state.stockType === "negative") {
            domain.push(["qty_available", "<", 0]);
        }
        const gt = parseFloat(this.state.greaterThan);
        if (this.state.greaterThan !== "" && !isNaN(gt)) {
            domain.push(["qty_available", ">", gt]);
        }
        this.props.onApply(domain);
    }

    clearFilters() {
        this.state.stockType = "";
        this.state.greaterThan = "";
        if (this.gtInput.el) this.gtInput.el.value = "";
        this.props.onClear();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Patch ListController
// ─────────────────────────────────────────────────────────────────────────────
patch(ListController.prototype, {

    setup() {
        super.setup(...arguments);
        this._isProductTemplate = (this.props.resModel === "product.template");
        this._stockExtraDomain = [];
        if (this._isProductTemplate) {
            this._stockBaseDomain = [...(this.props.domain || [])];
        }
    },

    get components() {
        return Object.assign({}, super.components, {
            ProductStockFilterBar,
        });
    },

    applyStockFilters(domain) {
        this._stockExtraDomain = domain;
        this._reloadStockDomain();
    },

    clearStockFilters() {
        this._stockExtraDomain = [];
        this._reloadStockDomain();
    },

    _reloadStockDomain() {
        const combined = [...this._stockBaseDomain, ...this._stockExtraDomain];
        if (this.model && this.model.root) {
            this.model.root.domain = combined;
            this.model.root.load({ keepSelection: false }).then(() => {
                this.model.notify();
            });
        }
    },
});