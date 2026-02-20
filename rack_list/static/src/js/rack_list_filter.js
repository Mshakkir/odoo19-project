/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
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
            locations: [],
        });

        onWillStart(async () => {
            try {
                const locs = await this.orm.call("rack.list", "get_locations", []);
                this.state.locations = locs;
            } catch (e) {
                console.error("[RackList] Could not load locations:", e);
            }
        });
    }

    onProductInput(ev) { this.state.productFilter = ev.target.value; }
    onLocationChange(ev) { this.state.locationId = ev.target.value; }

    onApply() {
        this.props.applyFilters({
            productFilter: this.state.productFilter.trim(),
            locationId: this.state.locationId,
        });
    }

    onClear() {
        this.state.productFilter = "";
        this.state.locationId = "";
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
        // Store current custom domain so we can combine with search panel
        this._rackDomain = [];
    }

    /**
     * Reload the model with the given domain.
     * In Odoo 17/18/19 the correct way to programmatically filter a list
     * is to call this.model.load({ domain }) which bypasses the search model
     * entirely and directly sets what records are fetched.
     */
    async applyRackFilters({ productFilter, locationId }) {
        const domain = [];

        if (productFilter) {
            domain.push("|",
                ["product_name", "ilike", productFilter],
                ["product_code", "ilike", productFilter]
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