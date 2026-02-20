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
        this._rackDomain = [];
    }

    async applyRackFilters({ productFilter, locationId }) {
        const domain = [];

        if (productFilter) {
            // product_name is jsonb (translatable) — cannot use ilike directly.
            // Use product_code (plain char) OR filter via the Many2one
            // product_id.name which Odoo ORM handles correctly for jsonb/translated fields.
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