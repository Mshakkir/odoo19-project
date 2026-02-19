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

        // Plain object — no useState needed, we update DOM directly
        this._rackSort = {
            field: "location_complete_name",
            order: "asc",
        };
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

    // ── Build and insert the sort bar into the DOM ──────────────────────────
    _mountSortBar() {
        // __owl__.bdom.el is the root DOM node of this controller component
        const rootEl = this.__owl__.bdom && this.__owl__.bdom.el;
        if (!rootEl || this._sortBarEl) return;

        const bar = document.createElement("div");
        bar.className =
            "rack_sort_bar d-flex align-items-center flex-wrap gap-2 " +
            "px-3 py-2 bg-white border-bottom shadow-sm";

        // Label
        const label = document.createElement("span");
        label.className = "fw-semibold text-secondary small me-1";
        label.innerHTML = '<i class="fa fa-filter me-1"></i>Sort by:';
        bar.appendChild(label);

        // Buttons
        for (const btn of SORT_BUTTONS) {
            const b = document.createElement("button");
            b.type = "button";
            b.dataset.sortField = btn.field;
            b.className =
                "btn btn-sm " +
                (this._rackSort.field === btn.field
                    ? "btn-primary"
                    : "btn-outline-secondary");
            b.title = "Sort by " + btn.label;
            b.innerHTML =
                btn.label +
                ` <i class="fa ms-1 ${this._iconFor(btn.field)}"></i>`;
            b.addEventListener("click", () => this._applySort(btn.field));
            bar.appendChild(b);
        }

        // Active-sort status text
        const status = document.createElement("span");
        status.className = "rack_sort_status ms-auto small text-muted fst-italic";
        bar.appendChild(status);
        this._renderStatus(status);

        this._sortBarEl = bar;

        // Insert the bar just before the controller root element
        rootEl.insertAdjacentElement("beforebegin", bar);
    }

    // ── Sync button classes/icons after any re-render ───────────────────────
    _refreshSortBar() {
        if (!this._sortBarEl) return;

        for (const btn of this._sortBarEl.querySelectorAll(
            "button[data-sort-field]"
        )) {
            const f = btn.dataset.sortField;
            btn.className =
                "btn btn-sm " +
                (this._rackSort.field === f
                    ? "btn-primary"
                    : "btn-outline-secondary");
            const icon = btn.querySelector("i.fa");
            if (icon) icon.className = "fa ms-1 " + this._iconFor(f);
        }

        const status = this._sortBarEl.querySelector(".rack_sort_status");
        if (status) this._renderStatus(status);
    }

    _renderStatus(el) {
        const dir =
            this._rackSort.order === "asc" ? "↑ Ascending" : "↓ Descending";
        el.innerHTML = `Sorted by <strong>${
            LABEL_MAP[this._rackSort.field] || this._rackSort.field
        }</strong> (${dir})`;
    }

    _iconFor(field) {
        if (this._rackSort.field !== field) return "fa-sort";
        return this._rackSort.order === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    // ── Apply sort: update state → update bar → reload list ─────────────────
    async _applySort(field) {
        if (this._rackSort.field === field) {
            this._rackSort.order =
                this._rackSort.order === "asc" ? "desc" : "asc";
        } else {
            this._rackSort.field = field;
            this._rackSort.order = "asc";
        }

        this._refreshSortBar();

        this.model.root.orderBy = [
            { name: field, asc: this._rackSort.order === "asc" },
        ];
        await this.model.root.load();
        this.render(true);
    }
}

// ── IMPORTANT: Do NOT assign .template — subclass inherits ListController's ──
export const rackListView = {
    ...listView,
    Controller: RackListController,
};

registry.category("views").add("rack_list", rackListView);