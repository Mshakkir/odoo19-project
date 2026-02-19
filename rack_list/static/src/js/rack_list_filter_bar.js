/** @odoo-module **/

import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

// ─── Autocomplete Input ───────────────────────────────────────────────────────
class FilterAutocomplete extends Component {
    static template = "rack_list.FilterAutocomplete";
    static props = {
        placeholder: String,
        fetchOptions: Function,
        onSelect: Function,
        onClear: Function,
    };

    setup() {
        this.state = useState({
            inputValue: "",
            suggestions: [],
            open: false,
            activeIdx: -1,
        });
        this.wrapperRef = useRef("wrapper");
        this._onDocClick = this._onDocClick.bind(this);
        document.addEventListener("click", this._onDocClick);
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick));
    }

    _onDocClick(ev) {
        const el = this.wrapperRef.el;
        if (el && !el.contains(ev.target)) {
            this.state.open = false;
        }
    }

    async onInput(ev) {
        const q = ev.target.value;
        this.state.inputValue = q;
        this.state.activeIdx = -1;
        if (!q) {
            this.props.onClear();
            this.state.suggestions = [];
            this.state.open = false;
            return;
        }
        this.state.suggestions = await this.props.fetchOptions(q);
        this.state.open = this.state.suggestions.length > 0;
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
        this.state.inputValue = option.label;
        this.state.open = false;
        this.state.suggestions = [];
        this.props.onSelect(option);
    }

    onClearClick() {
        this.state.inputValue = "";
        this.state.open = false;
        this.state.suggestions = [];
        this.props.onClear();
    }

    get hasValue() {
        return this.state.inputValue.length > 0;
    }
}

// ─── Filter Bar ───────────────────────────────────────────────────────────────
class RackListFilterBar extends Component {
    static template = "rack_list.FilterBar";
    static components = { FilterAutocomplete };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            productId: null,
            locationId: null,
        });
    }

    // Product autocomplete source
    async fetchProducts(query) {
        const results = await this.orm.call("product.product", "name_search", [], {
            name: query,
            limit: 8,
        });
        return results.map(([id, label]) => ({ id, label }));
    }

    // Location autocomplete source
    async fetchLocations(query) {
        const results = await this.orm.call("stock.location", "name_search", [], {
            name: query,
            args: [["usage", "=", "internal"]],
            limit: 8,
        });
        return results.map(([id, label]) => ({ id, label }));
    }

    onProductSelect(option) {
        this.state.productId = option.id;
        this._applyFilters();
    }

    onProductClear() {
        this.state.productId = null;
        this._applyFilters();
    }

    onLocationSelect(option) {
        this.state.locationId = option.id;
        this._applyFilters();
    }

    onLocationClear() {
        this.state.locationId = null;
        this._applyFilters();
    }

    _applyFilters() {
        const domain = [];
        if (this.state.productId) {
            domain.push(["product_id", "=", this.state.productId]);
        }
        if (this.state.locationId) {
            domain.push(["location_id", "=", this.state.locationId]);
        }
        try {
            // Odoo 16 / 17 / 18
            this.env.searchModel.setDomainParts({ rackListFilters: domain });
        } catch (_e) {
            // Fallback: toggle an invisible domain filter
            this.env.searchModel.query = domain;
        }
    }

    onApply() {
        this._applyFilters();
    }

    onClearAll() {
        this.state.productId = null;
        this.state.locationId = null;
        this.env.searchModel.setDomainParts({ rackListFilters: [] });
    }
}

// ─── Custom List Controller ───────────────────────────────────────────────────
class RackListController extends ListController {
    static template = "rack_list.ListController";
    static components = {
        ...ListController.components,
        RackListFilterBar,
    };
}

// ─── Register View ────────────────────────────────────────────────────────────
const rackListView = {
    ...listView,
    Controller: RackListController,
};

registry.category("views").add("rack_list_view", rackListView);