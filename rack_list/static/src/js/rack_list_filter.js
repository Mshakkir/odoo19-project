/** @odoo-module **/

/**
 * Rack List — Custom Filter Bar
 *
 * Uses js_class="rack_list_view" in the list arch to activate this custom view.
 * The custom view extends listView with a custom Controller that renders
 * a filter bar (product text input + location dropdown) above the list.
 */

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

    onProductInput(ev) {
        this.state.productFilter = ev.target.value;
    }

    onLocationChange(ev) {
        this.state.locationId = ev.target.value;
    }

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
// Custom List Controller
// ─────────────────────────────────────────────────────────────────────────────

class RackListController extends ListController {
    static template = "rack_list.ListController";
    static components = {
        ...ListController.components,
        RackListFilterBar,
    };

    applyRackFilters({ productFilter, locationId }) {
        const domain = [];

        if (productFilter) {
            domain.push(
                "|",
                ["product_name", "ilike", productFilter],
                ["product_code", "ilike", productFilter]
            );
        }

        if (locationId) {
            domain.push(["location_id", "=", parseInt(locationId, 10)]);
        }

        this.env.searchModel.setDomainParts({
            rackListCustomFilter: { domain, facets: [] },
        });
    }

    clearRackFilters() {
        this.env.searchModel.setDomainParts({
            rackListCustomFilter: { domain: [], facets: [] },
        });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Register the view — key must match js_class in the XML arch
// ─────────────────────────────────────────────────────────────────────────────

registry.category("views").add("rack_list_view", {
    ...listView,
    Controller: RackListController,
    display_name: "Rack List",
    multiRecord: true,
});