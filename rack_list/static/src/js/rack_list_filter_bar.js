/** @odoo-module **/

import { Component, App, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { templates } from "@web/core/assets";

// ─── Autocomplete Input ───────────────────────────────────────────────────────
class FilterAutocomplete extends Component {
    static template = "rack_list.FilterAutocomplete";
    static props = {
        placeholder: String,
        fetchOptions: Function,
        onSelect:     Function,
        onClear:      Function,
    };

    setup() {
        this.state = useState({
            inputValue: "",
            suggestions: [],
            open:      false,
            activeIdx: -1,
        });
        this.wrapperRef = useRef("wrapper");
        this._onDocClick = this._onDocClick.bind(this);
        document.addEventListener("click", this._onDocClick);
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick));
    }

    _onDocClick(ev) {
        const el = this.wrapperRef.el;
        if (el && !el.contains(ev.target)) this.state.open = false;
    }

    async onInput(ev) {
        const q = ev.target.value;
        this.state.inputValue = q;
        this.state.activeIdx  = -1;
        if (!q) {
            this.props.onClear();
            this.state.suggestions = [];
            this.state.open        = false;
            return;
        }
        this.state.suggestions = await this.props.fetchOptions(q);
        this.state.open        = this.state.suggestions.length > 0;
    }

    onKeyDown(ev) {
        const { suggestions, activeIdx, open } = this.state;
        if (!open) return;
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.activeIdx = Math.min(activeIdx + 1, suggestions.length - 1);
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.activeIdx = Math.max(activeIdx - 1, 0);
        } else if (ev.key === "Enter" && activeIdx >= 0) {
            ev.preventDefault();
            this.selectOption(suggestions[activeIdx]);
        } else if (ev.key === "Escape") {
            this.state.open = false;
        }
    }

    selectOption(option) {
        this.state.inputValue  = option.label;
        this.state.open        = false;
        this.state.suggestions = [];
        this.props.onSelect(option);
    }

    onClearClick() {
        this.state.inputValue  = "";
        this.state.open        = false;
        this.state.suggestions = [];
        this.props.onClear();
    }

    get hasValue() { return this.state.inputValue.length > 0; }
}

// ─── Filter Bar ───────────────────────────────────────────────────────────────
class RackListFilterBar extends Component {
    static template   = "rack_list.FilterBar";
    static components = { FilterAutocomplete };

    setup() {
        this.orm   = useService("orm");
        this.state = useState({ productId: null, locationId: null });
    }

    async fetchProducts(query) {
        const res = await this.orm.call("product.product", "name_search", [], {
            name: query, limit: 8,
        });
        return res.map(([id, label]) => ({ id, label }));
    }

    async fetchLocations(query) {
        const res = await this.orm.call("stock.location", "name_search", [], {
            name: query,
            args: [["usage", "=", "internal"]],
            limit: 8,
        });
        return res.map(([id, label]) => ({ id, label }));
    }

    onProductSelect(opt)  { this.state.productId  = opt.id;  this._apply(); }
    onProductClear()       { this.state.productId  = null;    this._apply(); }
    onLocationSelect(opt) { this.state.locationId = opt.id;  this._apply(); }
    onLocationClear()      { this.state.locationId = null;    this._apply(); }

    _apply() {
        const domain = [];
        if (this.state.productId)  domain.push(["product_id",  "=", this.state.productId]);
        if (this.state.locationId) domain.push(["location_id", "=", this.state.locationId]);
        this.env.searchModel.setDomainParts({ rackListFilters: domain });
    }

    onApply()    { this._apply(); }
    onClearAll() {
        this.state.productId  = null;
        this.state.locationId = null;
        this.env.searchModel.setDomainParts({ rackListFilters: [] });
    }
}

// ─── Custom Controller ────────────────────────────────────────────────────────
// NO static template override — we don't inherit any OWL template.
// Instead we mount RackListFilterBar directly into the control panel DOM
// via onMounted, sharing the parent env so searchModel is accessible.
class RackListController extends ListController {
    setup() {
        super.setup();
        this._filterApp       = null;
        this._filterContainer = null;

        onMounted(() => this._mountFilterBar());
        onWillUnmount(() => this._destroyFilterBar());
    }

    _mountFilterBar() {
        // Walk up to the action manager then down into the control panel slot.
        // .o_control_panel_bottom_left is the same area the Invoice filter row lives in.
        const anchor = document
            .querySelector(".o_action_manager .o_control_panel_bottom .o_control_panel_bottom_left");

        if (!anchor) return;

        // Avoid double-mounting if the action stays alive
        if (anchor.querySelector(".rack_filter_bar")) return;

        const container = document.createElement("div");
        anchor.prepend(container);
        this._filterContainer = container;

        // Mount as a separate OWL App but share THIS component's env so that
        // env.searchModel, env.services etc. are all available inside the bar.
        this._filterApp = new App(RackListFilterBar, {
            env: this.env,
            templates,
        });
        this._filterApp.mount(container);
    }

    _destroyFilterBar() {
        this._filterApp?.destroy();
        this._filterContainer?.remove();
        this._filterApp       = null;
        this._filterContainer = null;
    }
}

// ─── Register View ────────────────────────────────────────────────────────────
registry.category("views").add("rack_list_view", {
    ...listView,
    Controller: RackListController,
});