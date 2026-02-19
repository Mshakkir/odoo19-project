/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { Component, useState, useEffect, useRef, xml } from "@odoo/owl";

// ── Standalone Sort Bar Component ────────────────────────────────────────────
class RackSortBar extends Component {
    static template = xml`
        <div class="rack_sort_bar d-flex align-items-center flex-wrap gap-2 px-3 py-2 bg-white border-bottom shadow-sm">
            <span class="fw-semibold text-secondary small me-1">
                <i class="fa fa-filter me-1"/>Sort by:
            </span>

            <t t-foreach="props.buttons" t-as="btn" t-key="btn.field">
                <button
                    t-att-class="'btn btn-sm ' + (props.activeField === btn.field ? 'btn-primary' : 'btn-outline-secondary')"
                    t-on-click="() => props.onSort(btn.field)"
                    t-att-title="'Sort by ' + btn.label">
                    <t t-esc="btn.label"/>
                    <i t-att-class="'fa ms-1 ' + getIcon(btn.field)"/>
                </button>
            </t>

            <span t-if="props.activeField" class="ms-auto small text-muted fst-italic">
                Sorted by
                <strong t-esc="getLabel(props.activeField)"/>
                (<t t-esc="props.activeOrder === 'asc' ? '↑ Ascending' : '↓ Descending'"/>)
            </span>
        </div>
    `;

    static props = ["buttons", "activeField", "activeOrder", "onSort"];

    getIcon(field) {
        if (this.props.activeField !== field) return "fa-sort";
        return this.props.activeOrder === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    getLabel(field) {
        const map = {
            product_name: "Product",
            location_complete_name: "Location",
            quantity: "Qty",
        };
        return map[field] || field;
    }
}

// ── Rack List Controller ──────────────────────────────────────────────────────
class RackListController extends ListController {
    setup() {
        super.setup(...arguments);

        this.rackSort = useState({
            field: "location_complete_name",
            order: "asc",
        });

        this.sortBarRef = useRef("sortBarAnchor");

        // Mount the sort bar into the anchor div after the view renders
        useEffect(() => {
            const anchor = this.sortBarRef.el;
            if (!anchor) return;
            // Mount OWL sub-component into the anchor
            const app = this.__owl__.app;
            const sortBar = app.createComponent(RackSortBar, {
                buttons: [
                    { field: "product_name",          label: "Product"  },
                    { field: "location_complete_name", label: "Location" },
                    { field: "quantity",              label: "Qty"      },
                ],
                activeField: this.rackSort.field,
                activeOrder: this.rackSort.order,
                onSort: (field) => this.applySort(field),
            }, { env: this.env });
            sortBar.mount(anchor);
            return () => sortBar.destroy();
        });
    }

    async applySort(field) {
        if (this.rackSort.field === field) {
            this.rackSort.order = this.rackSort.order === "asc" ? "desc" : "asc";
        } else {
            this.rackSort.field = field;
            this.rackSort.order = "asc";
        }
        const asc = this.rackSort.order === "asc";
        this.model.root.orderBy = [{ name: field, asc }];
        await this.model.root.load();
        this.render(true);
    }
}

// Use the standard ListController template — no custom template needed
RackListController.template = "web.ListController";

export const rackListView = {
    ...listView,
    Controller: RackListController,
};

registry.category("views").add("rack_list", rackListView);