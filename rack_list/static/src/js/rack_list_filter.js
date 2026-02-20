/** @odoo-module **/

import { Component, useState, onWillStart, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

// ─────────────────────────────────────────────────────────────────────────────
// Filter Bar Component
// ─────────────────────────────────────────────────────────────────────────────

export class RackListFilterBar extends Component {
    static template = "rack_list.FilterBar";
    static props = {
        applyFilters: Function,
        clearFilters: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            productFilter: "",
            locationId: "",
            locationSearch: "",
            locations: [],
            filteredLocations: [],
            dropdownOpen: false,
            selectedLocationName: "",
        });

        onWillStart(async () => {
            try {
                const locs = await this.orm.call("rack.list", "get_locations", []);
                this.state.locations = locs;
                this.state.filteredLocations = locs;
            } catch (e) {
                console.error("[RackList] Could not load locations:", e);
            }
        });

        this.boundClose = (ev) => {
            const el = document.querySelector(".rack_loc_dropdown_wrap");
            if (el && !el.contains(ev.target)) {
                this.state.dropdownOpen = false;
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

    // ── Keyboard shortcut handler ──────────────────────────────────────────
    onKeyDown(ev) {
        if (ev.key === "Enter") {
            // Close dropdown if open, then apply filters
            this.state.dropdownOpen = false;
            this.onApply();
        } else if (ev.key === "Escape") {
            // Close dropdown if open, otherwise clear all filters
            if (this.state.dropdownOpen) {
                this.state.dropdownOpen = false;
            } else {
                this.onClear();
            }
        }
    }

    onProductInput(ev) { this.state.productFilter = ev.target.value; }

    onLocationSearchInput(ev) {
        const q = ev.target.value.toLowerCase();
        this.state.locationSearch = ev.target.value;
        this.state.filteredLocations = this.state.locations.filter(
            l => l.name.toLowerCase().includes(q)
        );
    }

    openDropdown() {
        this.state.dropdownOpen = true;
        this.state.locationSearch = "";
        this.state.filteredLocations = this.state.locations;
    }

    selectLocation(loc) {
        this.state.locationId = loc ? loc.id : "";
        this.state.selectedLocationName = loc ? loc.name : "";
        this.state.dropdownOpen = false;
    }

    clearLocation() {
        this.state.locationId = "";
        this.state.selectedLocationName = "";
        this.state.locationSearch = "";
        this.state.filteredLocations = this.state.locations;
        this.state.dropdownOpen = false;
    }

    onApply() {
        this.props.applyFilters({
            productFilter: this.state.productFilter.trim(),
            locationId: this.state.locationId,
        });
    }

    onClear() {
        this.state.productFilter = "";
        this.clearLocation();
        this.props.clearFilters();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Renderer
// ─────────────────────────────────────────────────────────────────────────────

class RackListRenderer extends ListRenderer {
    static template = "rack_list.ListRenderer";
    static components = {
        ...ListRenderer.components,
        RackListFilterBar,
    };

    applyRackFilters(filters) {
        const controller = this._getController();
        if (controller) controller.applyRackFilters(filters);
    }

    clearRackFilters() {
        const controller = this._getController();
        if (controller) controller.clearRackFilters();
    }

    _getController() {
        let node = this.__owl__.parent;
        while (node) {
            const comp = node.component;
            if (comp && comp.__IS_RACK_CONTROLLER__ === true) {
                return comp;
            }
            node = node.parent;
        }
        return null;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Controller
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
// Register view
// ─────────────────────────────────────────────────────────────────────────────

registry.category("views").add("rack_list_view", {
    ...listView,
    Controller: RackListController,
    Renderer: RackListRenderer,
    display_name: "Rack List",
    multiRecord: true,
});