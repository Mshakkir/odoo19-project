/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        // Only activate for stock ledger model
        if (this.props.resModel !== "product.stock.ledger.line") {
            return;
        }

        this._notif = useService("notification");
        this._filterEl = null;
        this._acTimeout = null;
        this._selectedProductId = null;

        onMounted(() => {
            // Delay to let OWL finish rendering the list table
            setTimeout(() => this._injectFilterBar(), 300);
        });

        onWillUnmount(() => {
            this._removeFilterBar();
        });
    },

    // ── Cleanup ─────────────────────────────────────────────────────────────
    _removeFilterBar() {
        if (this._filterEl) {
            this._filterEl.remove();
            this._filterEl = null;
        }
        if (this._acTimeout) {
            clearTimeout(this._acTimeout);
            this._acTimeout = null;
        }
    },

    // ── Inject the filter bar DOM above the list table ──────────────────────
    _injectFilterBar() {
        this._removeFilterBar();

        const table = document.querySelector(".o_list_table");
        if (!table) {
            // Table not rendered yet — retry once
            setTimeout(() => this._injectFilterBar(), 200);
            return;
        }

        // Prevent duplicate bars
        if (document.querySelector(".o_ledger_filter_bar")) return;

        const today      = new Date();
        const firstDay   = new Date(today.getFullYear(), today.getMonth(), 1);
        const dateTo     = today.toISOString().split("T")[0];
        const dateFrom   = firstDay.toISOString().split("T")[0];
        const uid        = Date.now();

        const bar = document.createElement("div");
        bar.className = "o_ledger_filter_bar";
        bar.style.cssText = `
            width:100%; background:#f8f9fa; border-bottom:2px solid #dee2e6;
            padding:10px 16px; box-sizing:border-box;
        `;
        bar.innerHTML = `
            <div style="display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;">

                <!-- Product autocomplete -->
                <div style="position:relative;min-width:170px;flex:1;">
                    <input id="lf_product_${uid}" type="text" autocomplete="off"
                        placeholder="Product name or code"
                        class="o_input" style="width:100%;font-size:12px;padding:4px 8px;"/>
                    <div id="lf_ac_${uid}"
                        style="display:none;position:absolute;top:100%;left:0;right:0;z-index:9999;
                               background:#fff;border:1px solid #ced4da;border-top:none;
                               border-radius:0 0 4px 4px;max-height:220px;overflow-y:auto;
                               box-shadow:0 4px 8px rgba(0,0,0,.12);"></div>
                </div>

                <!-- Warehouse -->
                <div style="min-width:130px;flex:1;">
                    <select id="lf_wh_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                        <option value="">Warehouse</option>
                    </select>
                </div>

                <!-- Date From → To -->
                <div style="display:flex;align-items:center;gap:6px;min-width:220px;flex:1;">
                    <input id="lf_df_${uid}" type="date" value="${dateFrom}"
                        class="o_input" style="flex:1;font-size:12px;padding:4px 6px;"/>
                    <span style="color:#6c757d;font-weight:bold;">→</span>
                    <input id="lf_dt_${uid}" type="date" value="${dateTo}"
                        class="o_input" style="flex:1;font-size:12px;padding:4px 6px;"/>
                </div>

                <!-- Voucher -->
                <div style="min-width:120px;flex:1;">
                    <input id="lf_voucher_${uid}" type="text" placeholder="Voucher"
                        class="o_input" style="width:100%;font-size:12px;padding:4px 8px;"/>
                </div>

                <!-- Type -->
                <div style="min-width:120px;flex:1;">
                    <select id="lf_type_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                        <option value="">Type</option>
                        <option value="Receipts">Receipts</option>
                        <option value="Delivery">Delivery</option>
                        <option value="Internal Transfer">Internal Transfer</option>
                    </select>
                </div>

                <!-- Invoice Status -->
                <div style="min-width:120px;flex:1;">
                    <select id="lf_inv_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                        <option value="">Invoice Status</option>
                        <option value="Invoiced">Invoiced</option>
                        <option value="Not Invoiced">Not Invoiced</option>
                        <option value="To Invoice">To Invoice</option>
                    </select>
                </div>

                <!-- Buttons -->
                <div style="display:flex;gap:8px;flex-shrink:0;">
                    <button id="lf_apply_${uid}" class="btn btn-primary btn-sm" style="font-size:12px;">Apply</button>
                    <button id="lf_clear_${uid}" class="btn btn-secondary btn-sm" style="font-size:12px;">Clear</button>
                </div>
            </div>
        `;

        table.parentElement.insertBefore(bar, table);
        this._filterEl = bar;

        this._loadWarehouses(uid);
        this._bindProductAutocomplete(uid);
        this._bindButtons(uid, dateFrom, dateTo);
    },

    // ── Load warehouse options ───────────────────────────────────────────────
    async _loadWarehouses(uid) {
        try {
            const rows = await this.orm.searchRead("stock.warehouse", [], ["id", "name"], { limit: 100 });
            const sel  = document.getElementById(`lf_wh_${uid}`);
            if (!sel) return;
            rows.forEach(({ id, name }) => {
                const opt = document.createElement("option");
                opt.value = id;
                opt.textContent = name;
                sel.appendChild(opt);
            });
        } catch (e) {
            console.warn("Ledger filter: could not load warehouses", e);
        }
    },

    // ── Product autocomplete ─────────────────────────────────────────────────
    _bindProductAutocomplete(uid) {
        const input = document.getElementById(`lf_product_${uid}`);
        const box   = document.getElementById(`lf_ac_${uid}`);
        if (!input || !box) return;

        const hide = () => { box.style.display = "none"; box.innerHTML = ""; };

        input.addEventListener("input", () => {
            const q = input.value.trim();
            this._selectedProductId = null;
            input.removeAttribute("data-pid");

            if (!q) { hide(); return; }
            if (this._acTimeout) clearTimeout(this._acTimeout);

            box.innerHTML = `<div style="padding:8px 12px;color:#6c757d;font-size:12px;">Searching…</div>`;
            box.style.display = "block";

            this._acTimeout = setTimeout(async () => {
                try {
                    const results = await this.orm.searchRead(
                        "product.product",
                        ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
                        ["id", "name", "display_name", "default_code"],
                        { limit: 20, order: "default_code asc, name asc" }
                    );
                    box.innerHTML = "";
                    if (!results.length) {
                        box.innerHTML = `<div style="padding:8px 12px;color:#6c757d;font-size:12px;">No products found</div>`;
                        box.style.display = "block";
                        return;
                    }
                    results.forEach(p => {
                        const div = document.createElement("div");
                        div.style.cssText = "padding:7px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #f0f0f0;display:flex;gap:8px;align-items:center;";
                        div.setAttribute("data-pid", p.id);
                        div.setAttribute("data-name", p.display_name || p.name);
                        const badge = p.default_code
                            ? `<span style="background:#e9ecef;color:#495057;border-radius:3px;padding:1px 5px;font-size:11px;font-weight:600;">[${p.default_code}]</span>`
                            : "";
                        div.innerHTML = `${badge}<span>${p.display_name || p.name}</span>`;
                        div.addEventListener("mouseenter", () => div.style.background = "#f0f7ff");
                        div.addEventListener("mouseleave", () => div.style.background = "");
                        div.addEventListener("mousedown", e => {
                            e.preventDefault();
                            this._selectedProductId = p.id;
                            input.value = p.display_name || p.name;
                            input.setAttribute("data-pid", p.id);
                            hide();
                        });
                        box.appendChild(div);
                    });
                    box.style.display = "block";
                } catch (err) {
                    console.warn("Ledger autocomplete error:", err);
                    hide();
                }
            }, 300);
        });

        input.addEventListener("blur", () => setTimeout(hide, 200));
    },

    // ── Apply / Clear buttons ────────────────────────────────────────────────
    _bindButtons(uid, defaultDateFrom, defaultDateTo) {
        const g = id => document.getElementById(id);
        const applyBtn  = g(`lf_apply_${uid}`);
        const clearBtn  = g(`lf_clear_${uid}`);
        if (!applyBtn || !clearBtn) return;

        applyBtn.addEventListener("click", () => {
            const domain = [];

            // Product
            const prodInput = g(`lf_product_${uid}`);
            const pid = prodInput && parseInt(prodInput.getAttribute("data-pid") || "0");
            if (pid) {
                domain.push(["product_id", "=", pid]);
            } else if (prodInput && prodInput.value.trim()) {
                domain.push(["|", ["product_id.name", "ilike", prodInput.value.trim()],
                                   ["product_id.default_code", "ilike", prodInput.value.trim()]]);
            }

            // Warehouse
            const wh = g(`lf_wh_${uid}`);
            if (wh && wh.value) domain.push(["warehouse_id", "=", parseInt(wh.value)]);

            // Dates
            const df = g(`lf_df_${uid}`);
            const dt = g(`lf_dt_${uid}`);
            if (df && dt && df.value && dt.value) {
                if (df.value > dt.value) {
                    this._notif.add("Start date must be before end date", { type: "warning" });
                    return;
                }
                domain.push(["date", ">=", df.value]);
                domain.push(["date", "<=", dt.value]);
            } else if (df && df.value) {
                domain.push(["date", ">=", df.value]);
            } else if (dt && dt.value) {
                domain.push(["date", "<=", dt.value]);
            }

            // Voucher
            const v = g(`lf_voucher_${uid}`);
            if (v && v.value.trim()) domain.push(["voucher", "ilike", v.value.trim()]);

            // Type  (field is move_type in the SQL view)
            const t = g(`lf_type_${uid}`);
            if (t && t.value) domain.push(["move_type", "=", t.value]);

            // Invoice status
            const inv = g(`lf_inv_${uid}`);
            if (inv && inv.value) domain.push(["invoice_status", "=", inv.value]);

            // Push domain to OWL model
            if (this.model && this.model.load) {
                this.model.load({ domain }).catch(e => console.warn("Filter apply warning:", e));
                this._notif.add("Filters applied", { type: "success" });
            }
        });

        clearBtn.addEventListener("click", () => {
            const prodInput = g(`lf_product_${uid}`);
            if (prodInput) { prodInput.value = ""; prodInput.removeAttribute("data-pid"); }
            this._selectedProductId = null;

            const wh  = g(`lf_wh_${uid}`);
            const df  = g(`lf_df_${uid}`);
            const dt  = g(`lf_dt_${uid}`);
            const v   = g(`lf_voucher_${uid}`);
            const t   = g(`lf_type_${uid}`);
            const inv = g(`lf_inv_${uid}`);

            if (wh)  wh.value  = "";
            if (df)  df.value  = defaultDateFrom;
            if (dt)  dt.value  = defaultDateTo;
            if (v)   v.value   = "";
            if (t)   t.value   = "";
            if (inv) inv.value = "";

            if (this.model && this.model.load) {
                this.model.load({ domain: [] }).catch(e => console.warn("Filter clear warning:", e));
                this._notif.add("Filters cleared", { type: "info" });
            }
        });
    },
});