/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";

const SORT_BUTTONS = [
    { field: "product_name",           label: "Product"  },
    { field: "location_complete_name", label: "Location" },
    { field: "quantity",               label: "Qty"      },
];

const LABEL_MAP = {
    product_name:           "Product",
    location_complete_name: "Location",
    quantity:               "Qty",
};

class RackListController extends ListController {
    setup() {
        super.setup(...arguments);

        this._rackSort = { field: null, order: "asc" };
        this._sortBarEl = null;

        onMounted(() => this._mountSortBar());
        onPatched(() => this._refreshSortBar());
        onWillUnmount(() => {
            if (this._sortBarEl) {
                this._sortBarEl.remove();
                this._sortBarEl = null;
            }
        });
    }

    _mountSortBar() {
        const rootEl = this.el || this.__owl__.bdom?.el;
        if (!rootEl || this._sortBarEl) return;

        const bar = document.createElement("div");
        bar.className =
            "rack_sort_bar d-flex align-items-center flex-wrap gap-2 " +
            "px-3 py-2 bg-white border-bottom shadow-sm";

        // "Sort by" label
        const label = document.createElement("span");
        label.className = "fw-semibold text-secondary small me-1";
        label.innerHTML = '<i class="fa fa-filter me-1"></i>Sort by:';
        bar.appendChild(label);

        // Sort buttons
        for (const btn of SORT_BUTTONS) {
            const b = document.createElement("button");
            b.type = "button";
            b.dataset.sortField = btn.field;
            b.className = "btn btn-sm btn-outline-secondary";
            b.title = "Sort by " + btn.label;
            b.innerHTML = `${btn.label} <i class="fa fa-sort ms-1"></i>`;
            b.addEventListener("click", () => this._applySort(btn.field));
            bar.appendChild(b);
        }

        // Status text on the right
        const status = document.createElement("span");
        status.className = "rack_sort_status ms-auto small text-muted fst-italic";
        bar.appendChild(status);

        this._sortBarEl = bar;
        rootEl.insertAdjacentElement("beforebegin", bar);
    }

    _refreshSortBar() {
        if (!this._sortBarEl) return;

        for (const btn of this._sortBarEl.querySelectorAll("button[data-sort-field]")) {
            const f = btn.dataset.sortField;
            const isActive = this._rackSort.field === f;
            btn.className = "btn btn-sm " + (isActive ? "btn-primary" : "btn-outline-secondary");
            const icon = btn.querySelector("i.fa");
            if (icon) icon.className = "fa ms-1 " + this._iconFor(f);
        }

        const status = this._sortBarEl.querySelector(".rack_sort_status");
        if (status) {
            if (this._rackSort.field) {
                const dir = this._rackSort.order === "asc" ? "↑ Ascending" : "↓ Descending";
                status.innerHTML = `Sorted by <strong>${LABEL_MAP[this._rackSort.field]}</strong> (${dir})`;
            } else {
                status.innerHTML = "";
            }
        }
    }

    _iconFor(field) {
        if (this._rackSort.field !== field) return "fa-sort";
        return this._rackSort.order === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    async _applySort(field) {
        // Toggle direction if same field, else reset to asc
        if (this._rackSort.field === field) {
            this._rackSort.order = this._rackSort.order === "asc" ? "desc" : "asc";
        } else {
            this._rackSort.field = field;
            this._rackSort.order = "asc";
        }

        this._refreshSortBar();

        // ✅ Use the correct Odoo API — never assign to orderBy directly
        // sortBy() toggles asc/desc internally; call twice if we need desc
        await this.model.root.sortBy(field);

        // If we need descending, sortBy sets asc first — call again to flip
        const currentOrder = this.model.root.orderBy;
        const isCurrentlyAsc = currentOrder?.[0]?.asc ?? true;
        if (this._rackSort.order === "desc" && isCurrentlyAsc) {
            await this.model.root.sortBy(field);
        } else if (this._rackSort.order === "asc" && !isCurrentlyAsc) {
            await this.model.root.sortBy(field);
        }
    }
}

export const rackListView = {
    ...listView,
    Controller: RackListController,
};

registry.category("views").add("rack_list", rackListView);