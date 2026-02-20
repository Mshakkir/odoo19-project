/** @odoo-module **/

import { Component, useState, onWillStart, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class RackListFilterBar extends Component {
    static template = "rack_list.FilterBar";
    static props = {
        applyFilters: Function,
        clearFilters: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            // Product
            productFilter: "",
            productSuggestions: [],
            productDropdownOpen: false,
            // Location
            locationId: "",
            locationSearch: "",
            locations: [],
            filteredLocations: [],
            locationDropdownOpen: false,
            selectedLocationName: "",
        });

        this._debounceTimer = null;

        onWillStart(async () => {
            try {
                const locs = await this.orm.call("rack.list", "get_locations", []);
                this.state.locations = locs;
                this.state.filteredLocations = locs;
            } catch (e) {
                console.error("[RackList] Could not load locations:", e);
            }
        });

        // Close dropdowns on outside click
        this.boundClose = (ev) => {
            const locEl = document.querySelector(".rack_loc_dropdown_wrap");
            if (locEl && !locEl.contains(ev.target)) {
                this.state.locationDropdownOpen = false;
            }
            const prodEl = document.querySelector(".rack_product_dropdown_wrap");
            if (prodEl && !prodEl.contains(ev.target)) {
                this.state.productDropdownOpen = false;
            }
        };

        useEffect(
            () => {
                document.addEventListener("mousedown", this.boundClose);
                return () => document.removeEventListener("mousedown", this.boundClose);
            },
            () => []
        );
    }

    // ── Product autocomplete ───────────────────────────────────────────────

    async onProductInput(ev) {
        const val = ev.target.value;
        this.state.productFilter = val;

        clearTimeout(this._debounceTimer);

        if (!val || val.trim().length === 0) {
            this.state.productSuggestions = [];
            this.state.productDropdownOpen = false;
            return;
        }

        // Debounce 200ms
        this._debounceTimer = setTimeout(async () => {
            try {
                const results = await this.orm.call(
                    "rack.list",
                    "search_products",
                    [val.trim()],
                    { limit: 15 }
                );
                this.state.productSuggestions = results;
                this.state.productDropdownOpen = results.length > 0;
            } catch (e) {
                console.error("[RackList] search_products error:", e);
                this.state.productSuggestions = [];
                this.state.productDropdownOpen = false;
            }
        }, 200);
    }

    selectProduct(suggestion) {
        // Fill input with selected product label and close dropdown
        this.state.productFilter = suggestion.label;
        this.state.productSuggestions = [];
        this.state.productDropdownOpen = false;
        // Auto-apply immediately on selection
        this.props.applyFilters({
            productFilter: suggestion.label,
            locationId: this.state.locationId,
        });
    }

    clearProduct() {
        clearTimeout(this._debounceTimer);
        this.state.productFilter = "";
        this.state.productSuggestions = [];
        this.state.productDropdownOpen = false;
    }

    // ── Keyboard shortcuts ─────────────────────────────────────────────────

    onKeyDown(ev) {
        if (ev.key === "Enter") {
            this.state.productDropdownOpen = false;
            this.state.locationDropdownOpen = false;
            this.onApply();
        } else if (ev.key === "Escape") {
            if (this.state.productDropdownOpen) {
                this.state.productDropdownOpen = false;
            } else if (this.state.locationDropdownOpen) {
                this.state.locationDropdownOpen = false;
            } else {
                this.onClear();
            }
        }
    }

    onLocationKeyDown(ev) {
        if (ev.key === "Enter") {
            ev.stopPropagation();
            if (this.state.filteredLocations.length === 1) {
                this.selectLocation(this.state.filteredLocations[0]);
            } else {
                this.state.locationDropdownOpen = false;
            }
            this.onApply();
        } else if (ev.key === "Escape") {
            ev.stopPropagation();
            this.state.locationDropdownOpen = false;
        }
    }

    // ── Location dropdown ──────────────────────────────────────────────────

    onLocationSearchInput(ev) {
        const q = ev.target.value.toLowerCase();
        this.state.locationSearch = ev.target.value;
        this.state.filteredLocations = this.state.locations.filter(
            l => l.name.toLowerCase().includes(q)
        );
    }

    openLocationDropdown() {
        this.state.locationDropdownOpen = true;
        this.state.locationSearch = "";
        this.state.filteredLocations = this.state.locations;
    }

    selectLocation(loc) {
        this.state.locationId = loc ? loc.id : "";
        this.state.selectedLocationName = loc ? loc.name : "";
        this.state.locationDropdownOpen = false;
    }

    clearLocation() {
        this.state.locationId = "";
        this.state.selectedLocationName = "";
        this.state.locationSearch = "";
        this.state.filteredLocations = this.state.locations;
        this.state.locationDropdownOpen = false;
    }

    // ── Apply / Clear ──────────────────────────────────────────────────────

    onApply() {
        this.props.applyFilters({
            productFilter: this.state.productFilter.trim(),
            locationId: this.state.locationId,
        });
    }

    onClear() {
        this.clearProduct();
        this.clearLocation();
        this.props.clearFilters();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Renderer
// ─────────────────────────────────────────────────────────────────────────────

class RackListRenderer extends ListRenderer {
    static template = "rack_list.ListRenderer";
    static components = {
        ...ListRenderer.components,
        RackListFilterBar,
    };

    applyRackFilters(filters) {
        const c = this._getController();
        if (c) c.applyRackFilters(filters);
    }

    clearRackFilters() {
        const c = this._getController();
        if (c) c.clearRackFilters();
    }

    _getController() {
        let node = this.__owl__.parent;
        while (node) {
            if (node.component && node.component.__IS_RACK_CONTROLLER__ === true) {
                return node.component;
            }
            node = node.parent;
        }
        return null;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Controller
// ─────────────────────────────────────────────────────────────────────────────

class RackListController extends ListController {
    static template = "rack_list.ListController";
    __IS_RACK_CONTROLLER__ = true;

    setup() {
        super.setup();
        this._rackDomain = [];
    }

    async applyRackFilters({ productFilter, locationId }) {
        const domain = [];
        if (productFilter) {
            domain.push("|",
                ["product_code", "ilike", productFilter],
                ["product_id.name", "ilike", productFilter]
            );
        }
        if (locationId) {
            domain.push(["location_id", "=", parseInt(locationId, 10)]);
        }
        this._rackDomain = domain;
        await this.model.load({ domain });
        this.render(true);
    }

    async clearRackFilters() {
        this._rackDomain = [];
        await this.model.load({ domain: [] });
        this.render(true);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Register
// ─────────────────────────────────────────────────────────────────────────────

registry.category("views").add("rack_list_view", {
    ...listView,
    Controller: RackListController,
    Renderer: RackListRenderer,
    display_name: "Rack List",
    multiRecord: true,
});