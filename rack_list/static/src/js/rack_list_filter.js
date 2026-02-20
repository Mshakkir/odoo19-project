/** @odoo-module **/

/**
 * Rack List - Custom Filter Bar
 *
 * Injects a filter bar (product input + location dropdown + Apply/Clear)
 * above the list view when the active model is `rack.list`.
 *
 * Strategy: patch ListController to add the filter bar component and wire up
 * domain injection via env.searchModel.setDomainParts().
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// ─────────────────────────────────────────────────────────────────────────────
// Filter Bar Component
// ─────────────────────────────────────────────────────────────────────────────

class RackListFilterBar extends Component {
    static template = "rack_list.FilterBar";
    static props = {
        applyFilters: { type: Function },
        clearFilters: { type: Function },
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
// Patch ListController
// ─────────────────────────────────────────────────────────────────────────────

patch(ListController, {
    components: {
        ...ListController.components,
        RackListFilterBar,
    },
});

patch(ListController.prototype, {
    /**
     * Returns true when this controller is managing the rack.list model.
     * Used by the template to decide whether to render the filter bar.
     */
    get isRackList() {
        return this.props.resModel === "rack.list";
    },

    /**
     * Build and inject a domain from the filter bar values into the search model.
     */
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
    },

    /**
     * Remove the custom domain injected by the filter bar.
     */
    clearRackFilters() {
        this.env.searchModel.setDomainParts({
            rackListCustomFilter: { domain: [], facets: [] },
        });
    },
});