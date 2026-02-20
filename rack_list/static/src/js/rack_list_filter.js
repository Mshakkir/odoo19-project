/** @odoo-module **/

import { Component, useState, onWillStart, useRef, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

// ─────────────────────────────────────────────────────────────────────────────
// Filter Bar Component
// ─────────────────────────────────────────────────────────────────────────────

class RackListFilterBar extends Component {
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

        // Close dropdown when clicking outside
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

    onProductInput(ev) {
        this.state.productFilter = ev.target.value;
    }

    // Location search filter
    onLocationSearchInput(ev) {
        const q = ev.target.value.toLowerCase();
        this.state.locationSearch = ev.target.value;
        this.state.filteredLocations = this.state.locations.filter(l =>
            l.name.toLowerCase().includes(q)
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
// Custom Controller
// ─────────────────────────────────────────────────────────────────────────────

class RackListController extends ListController {
    static template = "rack_list.ListController";
    static components = {
        ...ListController.components,
        RackListFilterBar,
    };

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
    display_name: "Rack List",
    multiRecord: true,
});