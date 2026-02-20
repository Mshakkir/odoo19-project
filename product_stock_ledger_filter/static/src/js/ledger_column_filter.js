/** @odoo-module **/
/**
 * Product Stock Ledger - Filter Bar
 * Uses MutationObserver to detect when the ledger list view is rendered,
 * then injects a plain HTML filter bar. No OWL patching — zero lifecycle risk.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

// ── Standalone OWL Component registered as a client action overlay ───────────
// This is NOT patching anything — it's a clean sideline observer.

let _filterInstance = null; // singleton guard

function buildFilterBar(orm, notification) {
    // Prevent duplicates
    if (document.querySelector(".o_sl_filter_bar")) return;

    const table = document.querySelector(".o_list_view .o_list_table");
    if (!table) return;

    const today    = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const dateTo   = today.toISOString().split("T")[0];
    const dateFrom = firstDay.toISOString().split("T")[0];
    const uid      = Date.now();

    const bar = document.createElement("div");
    bar.className = "o_sl_filter_bar";
    bar.setAttribute("data-uid", uid);
    bar.style.cssText = [
        "width:100%", "background:#f8f9fa", "border-bottom:2px solid #dee2e6",
        "padding:8px 16px", "box-sizing:border-box",
        "display:flex", "align-items:flex-end", "gap:8px", "flex-wrap:wrap",
    ].join(";");

    bar.innerHTML = `
        <div style="position:relative;min-width:160px;flex:1.5;">
            <input id="sl_prod_${uid}" type="text" autocomplete="off"
                placeholder="Product name or code"
                class="o_input" style="width:100%;font-size:12px;padding:4px 8px;"/>
            <div id="sl_ac_${uid}"
                style="display:none;position:absolute;top:100%;left:0;right:0;z-index:9999;
                       background:#fff;border:1px solid #ced4da;border-top:none;
                       border-radius:0 0 4px 4px;max-height:220px;overflow-y:auto;
                       box-shadow:0 4px 8px rgba(0,0,0,.12);"></div>
        </div>
        <div style="min-width:120px;flex:1;">
            <select id="sl_wh_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                <option value="">Warehouse</option>
            </select>
        </div>
        <div style="display:flex;align-items:center;gap:5px;min-width:210px;flex:1.5;">
            <input id="sl_df_${uid}" type="date" value="${dateFrom}"
                class="o_input" style="flex:1;font-size:12px;padding:4px 5px;"/>
            <span style="color:#888;font-weight:bold;">→</span>
            <input id="sl_dt_${uid}" type="date" value="${dateTo}"
                class="o_input" style="flex:1;font-size:12px;padding:4px 5px;"/>
        </div>
        <div style="min-width:110px;flex:1;">
            <input id="sl_vou_${uid}" type="text" placeholder="Voucher"
                class="o_input" style="width:100%;font-size:12px;padding:4px 8px;"/>
        </div>
        <div style="min-width:110px;flex:1;">
            <select id="sl_type_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                <option value="">Type</option>
                <option value="Receipts">Receipts</option>
                <option value="Delivery">Delivery</option>
                <option value="Internal Transfer">Internal Transfer</option>
            </select>
        </div>
        <div style="min-width:110px;flex:1;">
            <select id="sl_inv_${uid}" class="o_input" style="width:100%;font-size:12px;padding:4px 6px;">
                <option value="">Invoice Status</option>
                <option value="Invoiced">Invoiced</option>
                <option value="Not Invoiced">Not Invoiced</option>
                <option value="To Invoice">To Invoice</option>
            </select>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0;">
            <button id="sl_apply_${uid}" class="btn btn-primary btn-sm" style="font-size:12px;">Apply</button>
            <button id="sl_clear_${uid}" class="btn btn-secondary btn-sm" style="font-size:12px;">Clear</button>
        </div>
    `;

    // Insert bar above the list table
    table.closest(".o_list_view").insertBefore(bar, table.closest(".o_list_view").firstChild);

    // ── Load warehouses ──────────────────────────────────────────────────────
    orm.searchRead("stock.warehouse", [], ["id", "name"], { limit: 100 })
        .then(rows => {
            const sel = document.getElementById(`sl_wh_${uid}`);
            if (!sel) return;
            rows.forEach(({ id, name }) => {
                const o = document.createElement("option");
                o.value = id; o.textContent = name;
                sel.appendChild(o);
            });
        })
        .catch(e => console.warn("SL filter: warehouse load error", e));

    // ── Product autocomplete ─────────────────────────────────────────────────
    let acTimer = null;
    const prodInput = document.getElementById(`sl_prod_${uid}`);
    const acBox     = document.getElementById(`sl_ac_${uid}`);

    const hideAc = () => { acBox.style.display = "none"; acBox.innerHTML = ""; };

    prodInput.addEventListener("input", () => {
        const q = prodInput.value.trim();
        prodInput.removeAttribute("data-pid");
        if (!q) { hideAc(); return; }
        if (acTimer) clearTimeout(acTimer);
        acBox.innerHTML = `<div style="padding:8px 12px;color:#6c757d;font-size:12px;">Searching…</div>`;
        acBox.style.display = "block";
        acTimer = setTimeout(() => {
            orm.searchRead(
                "product.product",
                ["|", ["name","ilike",q], ["default_code","ilike",q]],
                ["id","name","display_name","default_code"],
                { limit: 20, order: "default_code asc, name asc" }
            ).then(results => {
                acBox.innerHTML = "";
                if (!results.length) {
                    acBox.innerHTML = `<div style="padding:8px 12px;color:#6c757d;font-size:12px;">No products found</div>`;
                    acBox.style.display = "block";
                    return;
                }
                results.forEach(p => {
                    const d = document.createElement("div");
                    d.style.cssText = "padding:6px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #f0f0f0;display:flex;gap:8px;align-items:center;";
                    d.setAttribute("data-pid", p.id);
                    const badge = p.default_code
                        ? `<span style="background:#e9ecef;color:#495057;border-radius:3px;padding:1px 5px;font-size:11px;font-weight:600;">[${p.default_code}]</span>`
                        : "";
                    d.innerHTML = `${badge}<span>${p.display_name || p.name}</span>`;
                    d.addEventListener("mouseenter", () => d.style.background = "#f0f7ff");
                    d.addEventListener("mouseleave", () => d.style.background = "");
                    d.addEventListener("mousedown", e => {
                        e.preventDefault();
                        prodInput.value = p.display_name || p.name;
                        prodInput.setAttribute("data-pid", p.id);
                        hideAc();
                    });
                    acBox.appendChild(d);
                });
                acBox.style.display = "block";
            }).catch(() => hideAc());
        }, 300);
    });
    prodInput.addEventListener("blur", () => setTimeout(hideAc, 200));

    // ── Apply / Clear ────────────────────────────────────────────────────────
    const g = id => document.getElementById(id);

    const getListRenderer = () => {
        // Walk OWL component tree to find the list model
        const listView = document.querySelector(".o_list_view");
        if (!listView) return null;
        let el = listView;
        while (el) {
            if (el.__owl__ && el.__owl__.component && el.__owl__.component.model) {
                return el.__owl__.component;
            }
            el = el.firstElementChild;
        }
        return null;
    };

    const applyDomain = (domain) => {
        const comp = getListRenderer();
        if (comp && comp.model && comp.model.load) {
            comp.model.load({ domain }).catch(e => console.warn("SL filter domain error:", e));
        } else {
            console.warn("SL filter: could not find list model component");
        }
    };

    g(`sl_apply_${uid}`).addEventListener("click", () => {
        const domain = [];

        const pi = g(`sl_prod_${uid}`);
        const pid = pi && parseInt(pi.getAttribute("data-pid") || "0");
        if (pid) {
            domain.push(["product_id", "=", pid]);
        } else if (pi && pi.value.trim()) {
            domain.push(["|",
                ["product_id.name", "ilike", pi.value.trim()],
                ["product_id.default_code", "ilike", pi.value.trim()]
            ]);
        }

        const wh = g(`sl_wh_${uid}`);
        if (wh && wh.value) domain.push(["warehouse_id", "=", parseInt(wh.value)]);

        const df = g(`sl_df_${uid}`);
        const dt = g(`sl_dt_${uid}`);
        if (df && df.value) domain.push(["date", ">=", df.value]);
        if (dt && dt.value) domain.push(["date", "<=", dt.value]);
        if (df && dt && df.value && dt.value && df.value > dt.value) {
            notification.add("Start date must be before end date", { type: "warning" });
            return;
        }

        const vo = g(`sl_vou_${uid}`);
        if (vo && vo.value.trim()) domain.push(["voucher", "ilike", vo.value.trim()]);

        const ty = g(`sl_type_${uid}`);
        if (ty && ty.value) domain.push(["move_type", "=", ty.value]);

        const iv = g(`sl_inv_${uid}`);
        if (iv && iv.value) domain.push(["invoice_status", "=", iv.value]);

        applyDomain(domain);
        notification.add("Filters applied", { type: "success" });
    });

    g(`sl_clear_${uid}`).addEventListener("click", () => {
        const pi = g(`sl_prod_${uid}`);
        if (pi) { pi.value = ""; pi.removeAttribute("data-pid"); }
        const wh = g(`sl_wh_${uid}`); if (wh) wh.value = "";
        const df = g(`sl_df_${uid}`); if (df) df.value = dateFrom;
        const dt = g(`sl_dt_${uid}`); if (dt) dt.value = dateTo;
        const vo = g(`sl_vou_${uid}`); if (vo) vo.value = "";
        const ty = g(`sl_type_${uid}`); if (ty) ty.value = "";
        const iv = g(`sl_inv_${uid}`); if (iv) iv.value = "";
        applyDomain([]);
        notification.add("Filters cleared", { type: "info" });
    });
}

// ── MutationObserver service: watches for ledger list view appearing ──────────
registry.category("services").add("stock_ledger_filter_observer", {
    dependencies: ["orm", "notification"],
    start(env, { orm, notification }) {
        let observer = null;
        let debounce = null;

        const check = () => {
            // Only inject when URL/action is the ledger model
            const isLedger = !!document.querySelector(
                ".o_list_view[class*='o_list']"
            ) && !!document.querySelector(".o_list_table");

            if (!isLedger) {
                // Remove bar if navigated away
                document.querySelector(".o_sl_filter_bar")?.remove();
                return;
            }

            // Check if this list is the stock ledger (look for its unique columns)
            // We detect by checking breadcrumb or the action in the URL
            const breadcrumb = document.querySelector(".o_breadcrumb .o_last_breadcrumb_item");
            if (!breadcrumb) return;
            const title = breadcrumb.textContent.trim().toLowerCase();
            if (!title.includes("stock ledger") && !title.includes("product stock ledger")) return;

            buildFilterBar(orm, notification);
        };

        const scheduleCheck = () => {
            if (debounce) clearTimeout(debounce);
            debounce = setTimeout(check, 400);
        };

        observer = new MutationObserver(scheduleCheck);
        observer.observe(document.body, { childList: true, subtree: true });

        return {
            destroy() {
                if (observer) observer.disconnect();
                document.querySelector(".o_sl_filter_bar")?.remove();
            }
        };
    }
});