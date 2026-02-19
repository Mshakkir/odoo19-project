/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useState } from "@odoo/owl";

class RackListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.rackSort = useState({
            field: "location_complete_name",
            order: "asc",
        });
    }

    /**
     * Returns the sort button definitions.
     * @returns {Array<{field: string, label: string}>}
     */
    get sortButtons() {
        return [
            { field: "product_name",           label: "Product"  },
            { field: "location_complete_name",  label: "Location" },
            { field: "quantity",               label: "Qty"      },
        ];
    }

    /**
     * Returns the appropriate FontAwesome icon class for the given field.
     * @param {string} field
     * @returns {string}
     */
    getSortIcon(field) {
        if (this.rackSort.field !== field) return "fa-sort";
        return this.rackSort.order === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    /**
     * Applies sorting by field; toggles direction if same field clicked again.
     * Removes groupBy so individual row ordering works correctly.
     * @param {string} field
     */
    async applySort(field) {
        const isSameField = this.rackSort.field === field;

        if (isSameField) {
            this.rackSort.order = this.rackSort.order === "asc" ? "desc" : "asc";
        } else {
            this.rackSort.field = field;
            this.rackSort.order = "asc";
        }

        // If the list is currently grouped, ungrouping gives accurate row-level sort
        const searchModel = this.env.searchModel;
        if (searchModel) {
            // Remove any active groupBy so sort takes full effect on rows
            const groupBys = searchModel.getSearchItems((item) => item.type === "groupBy" && item.isActive);
            for (const gb of groupBys) {
                searchModel.toggleSearchItem(gb.id);
            }
        }

        // Apply sort through the list model
        await this.model.root.sortBy(field);

        // Sync our display state with the model's actual order
        const orderBy = this.model.root.orderBy;
        if (orderBy && orderBy.length) {
            this.rackSort.field = orderBy[0].name;
            this.rackSort.order = orderBy[0].asc ? "asc" : "desc";
        }
    }
}

RackListController.template = "rack_list.ListController";

export const rackListView = {
    ...listView,
    Controller: RackListController,
};

registry.category("views").add("rack_list", rackListView);