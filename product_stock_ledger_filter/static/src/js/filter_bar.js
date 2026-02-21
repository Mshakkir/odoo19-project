/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("services").add("stock_ledger_filter", {
    dependencies: ["orm"],
    start(env, { orm }) {

        let debounce = null;

        function isStockLedgerView() {
            const candidates = document.querySelectorAll(
                ".o_breadcrumb .o_last_breadcrumb_item span, " +
                ".o_breadcrumb .active, " +
                ".o_breadcrumb span"
            );
            for (const el of candidates) {
                if (el.textContent.trim().toLowerCase().includes("stock ledger")) return true;
            }
            return false;
        }

        // Walk the OWL tree to find list model — try multiple strategies
        function getListModel() {
            const selectors = [".o_list_renderer", ".o_list_view", ".o_view_controller"];
            for (const sel of selectors) {
                let el = document.querySelector(sel);
                // Walk down
                let cur = el;
                while (cur) {
                    if (cur.__owl__?.component?.model) return cur.__owl__.component.model;
                    cur = cur.firstElementChild;
                }
                // Walk up from table
                cur = document.querySelector(".o_list_table");
                while (cur && cur !== document.body) {
                    if (cur.__owl__?.component?.model) return cur.__owl__.component.model;
                    cur = cur.parentElement;
                }
            }
            return null;
        }

        function applyDomain(domain) {
            const model = getListModel();
            if (!model?.root) {
                console.warn("[SLFilter] model not found");
                return;
            }
            model.root.domain = domain;
            model.root.load()
                .then(() => model.notify())
                .catch(e => console.warn("[SLFilter] load error", e));
        }

        function buildBar() {
            if (document.querySelector(".o_sl_filter_bar")) return;

            // ── Find insertion point ──────────────────────────────────
            // In Odoo 19 the layout inside .o_action_manager is:
            //   .o_view_controller (or .o_action)
            //     .o_control_panel        ← search bar
            //     .o_content              ← contains .o_list_view
            //       .o_list_view
            //
            // We want the bar INSIDE .o_content, BEFORE .o_list_view

            const listView = document.querySelector(".o_list_view");
            if (!listView) return;

            // Try to find .o_content first
            let insertParent = null;
            let insertBefore = null;

            const oContent = document.querySelector(".o_content");
            if (oContent && oContent.contains(listView)) {
                insertParent = oContent;
                insertBefore = listView;
            } else {
                // Fallback: use listView's direct parent
                insertParent = listView.parentElement;
                insertBefore = listView;
            }

            if (!insertParent) return;

            const uid = Date.now();

            const bar = document.createElement("div");
            bar.className = "o_sl_filter_bar";

            bar.innerHTML = `
                <div class="slf-wrap">
                    <div class="slf-field slf-field-prod">
                        <input id="slf_prod_${uid}" type="text" class="slf-input"
                            placeholder="Product name or code" autocomplete="off"/>
                        <div id="slf_ac_${uid}" class="slf-autocomplete"></div>
                    </div>
                    <div class="slf-field">
                        <select id="slf_wh_${uid}" class="slf-input">
                            <option value="">Warehouse</option>
                        </select>
                    </div>
                    <div class="slf-date-wrap">
                        <input id="slf_df_${uid}" type="date" class="slf-input slf-date"/>
                        <span class="slf-arrow">→</span>
                        <input id="slf_dt_${uid}" type="date" class="slf-input slf-date"/>
                    </div>
                    <div class="slf-field">
                        <input id="slf_vou_${uid}" type="text" class="slf-input" placeholder="Voucher"/>
                    </div>
                    <div class="slf-field slf-field-sm">
                        <select id="slf_type_${uid}" class="slf-input">
                            <option value="">Type</option>
                            <option value="IN">IN</option>
                            <option value="OUT">OUT</option>
                            <option value="INT">INT</option>
                        </select>
                    </div>
                    <div class="slf-field">
                        <select id="slf_inv_${uid}" class="slf-input">
                            <option value="">Invoice Status</option>
                            <option value="invoiced">Invoiced</option>
                            <option value="to invoice">To Invoice</option>
                            <option value="nothing">Nothing</option>
                        </select>
                    </div>
                    <div class="slf-actions">
                        <button id="slf_apply_${uid}" class="slf-btn slf-btn-apply">
                            Apply <kbd>↵</kbd>
                        </button>
                        <button id="slf_clear_${uid}" class="slf-btn slf-btn-clear">
                            Clear <kbd>Esc</kbd>
                        </button>
                    </div>
                </div>
            `;

            // ✅ Insert inside .o_content, directly before .o_list_view
            insertParent.insertBefore(bar, insertBefore);

            // ── Warehouses ────────────────────────────────────────────
            orm.searchRead("stock.warehouse", [], ["id", "name"], { limit: 200 })
                .then(rows => {
                    const sel = document.getElementById(`slf_wh_${uid}`);
                    if (!sel) return;
                    rows.forEach(({ id, name }) => {
                        const opt = document.createElement("option");
                        opt.value = id; opt.textContent = name;
                        sel.appendChild(opt);
                    });
                }).catch(() => {});

            // ── Product autocomplete ──────────────────────────────────
            const prodInput = document.getElementById(`slf_prod_${uid}`);
            const acBox     = document.getElementById(`slf_ac_${uid}`);
            let   acTimer   = null;

            const hideAc = () => { acBox.style.display = "none"; acBox.innerHTML = ""; };

            prodInput.addEventListener("input", () => {
                prodInput.removeAttribute("data-pid");
                const q = prodInput.value.trim();
                if (!q) { hideAc(); return; }
                if (acTimer) clearTimeout(acTimer);
                acBox.innerHTML = `<div class="slf-ac-item" style="color:#999">Searching…</div>`;
                acBox.style.display = "block";
                acTimer = setTimeout(() => {
                    orm.searchRead(
                        "product.product",
                        ["|", ["name","ilike",q], ["default_code","ilike",q]],
                        ["id","display_name","default_code"],
                        { limit: 20, order: "default_code asc, name asc" }
                    ).then(results => {
                        acBox.innerHTML = "";
                        if (!results.length) {
                            acBox.innerHTML = `<div class="slf-ac-item" style="color:#999">No results</div>`;
                            acBox.style.display = "block";
                            return;
                        }
                        results.forEach(p => {
                            const d = document.createElement("div");
                            d.className = "slf-ac-item";
                            const badge = p.default_code
                                ? `<span class="slf-badge">[${p.default_code}]</span>` : "";
                            d.innerHTML = `${badge}<span>${p.display_name||p.name}</span>`;
                            d.addEventListener("mousedown", e => {
                                e.preventDefault();
                                prodInput.value = p.display_name;
                                prodInput.setAttribute("data-pid", p.id);
                                hideAc();
                            });
                            acBox.appendChild(d);
                        });
                        acBox.style.display = "block";
                    }).catch(() => hideAc());
                }, 280);
            });
            prodInput.addEventListener("blur", () => setTimeout(hideAc, 180));

            // ── Helpers ───────────────────────────────────────────────
            const g = id => document.getElementById(id);

            const getDomain = () => {
                const domain = [];
                const pi  = g(`slf_prod_${uid}`);
                const pid = parseInt(pi?.getAttribute("data-pid") || "0");
                if (pid) {
                    domain.push(["product_id", "=", pid]);
                } else if (pi?.value.trim()) {
                    domain.push(["product_id.display_name", "ilike", pi.value.trim()]);
                }
                const wh = g(`slf_wh_${uid}`);
                if (wh?.value) domain.push(["warehouse_id", "=", parseInt(wh.value)]);
                const df = g(`slf_df_${uid}`);
                const dt = g(`slf_dt_${uid}`);
                if (df?.value) domain.push(["date", ">=", df.value + " 00:00:00"]);
                if (dt?.value) domain.push(["date", "<=", dt.value + " 23:59:59"]);
                const vo = g(`slf_vou_${uid}`);
                if (vo?.value.trim()) domain.push(["voucher", "ilike", vo.value.trim()]);
                const ty = g(`slf_type_${uid}`);
                if (ty?.value) domain.push(["move_type", "=", ty.value]);
                const iv = g(`slf_inv_${uid}`);
                if (iv?.value) domain.push(["invoice_status", "=", iv.value]);
                return domain;
            };

            // ✅ Apply: wait for model to be ready, retry up to 10 times
            const doApply = () => {
                const domain = getDomain();
                let tries = 0;
                const attempt = () => {
                    const model = getListModel();
                    if (model?.root) {
                        model.root.domain = domain;
                        model.root.load()
                            .then(() => model.notify())
                            .catch(e => console.warn("[SLFilter] apply error", e));
                    } else if (tries++ < 10) {
                        setTimeout(attempt, 200);
                    }
                };
                attempt();
            };

            const doClear = () => {
                ["slf_wh_","slf_type_","slf_inv_"].forEach(k => {
                    const el = g(k + uid); if (el) el.value = "";
                });
                ["slf_df_","slf_dt_","slf_vou_"].forEach(k => {
                    const el = g(k + uid); if (el) el.value = "";
                });
                const pi = g(`slf_prod_${uid}`);
                if (pi) { pi.value = ""; pi.removeAttribute("data-pid"); }
                applyDomain([]);
            };

            g(`slf_apply_${uid}`).addEventListener("click", doApply);
            g(`slf_clear_${uid}`).addEventListener("click", doClear);

            // ✅ Keyboard: Enter = Apply, Esc = Clear
            const onKey = e => {
                if (document.querySelector(".o_dialog, .modal.show")) return;
                const active    = document.activeElement;
                const inBar     = bar.contains(active);
                const inOtherInput = !inBar && (
                    active.tagName === "INPUT" ||
                    active.tagName === "TEXTAREA" ||
                    active.tagName === "SELECT"
                );
                if (inOtherInput) return;
                if (e.key === "Enter")  { e.preventDefault(); doApply(); }
                if (e.key === "Escape") { e.preventDefault(); doClear(); }
            };
            document.addEventListener("keydown", onKey);
            bar._cleanup = () => document.removeEventListener("keydown", onKey);
        }

        // ── MutationObserver ──────────────────────────────────────────
        const observer = new MutationObserver(() => {
            if (debounce) clearTimeout(debounce);
            debounce = setTimeout(() => {
                const existingBar = document.querySelector(".o_sl_filter_bar");
                if (!isStockLedgerView()) {
                    if (existingBar) {
                        if (existingBar._cleanup) existingBar._cleanup();
                        existingBar.remove();
                    }
                    return;
                }
                if (!existingBar && document.querySelector(".o_list_view .o_list_table")) {
                    buildBar();
                }
            }, 400);
        });

        observer.observe(document.body, { childList: true, subtree: true });

        return {
            destroy() {
                observer.disconnect();
                const bar = document.querySelector(".o_sl_filter_bar");
                if (bar) { if (bar._cleanup) bar._cleanup(); bar.remove(); }
            }
        };
    }
});









///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//
//registry.category("services").add("stock_ledger_filter", {
//    dependencies: ["orm", "notification"],
//    start(env, { orm, notification }) {
//
//        let debounce = null;
//
//        function isStockLedgerView() {
//            const breadcrumb = document.querySelector(
//                ".o_breadcrumb .o_last_breadcrumb_item span, " +
//                ".o_breadcrumb .active"
//            );
//            if (!breadcrumb) return false;
//            return breadcrumb.textContent.trim().toLowerCase().includes("stock ledger");
//        }
//
//        function getListModel() {
//            // Try walking down from .o_list_view
//            let el = document.querySelector(".o_list_view");
//            while (el) {
//                if (el.__owl__?.component?.model) return el.__owl__.component.model;
//                el = el.firstElementChild;
//            }
//            // Try walking up from list table
//            el = document.querySelector(".o_list_table");
//            while (el && el !== document.body) {
//                if (el.__owl__?.component?.model) return el.__owl__.component.model;
//                el = el.parentElement;
//            }
//            return null;
//        }
//
//        function applyDomain(domain) {
//            const model = getListModel();
//            if (model?.root) {
//                model.root.domain = domain;
//                model.root.load().then(() => model.notify()).catch(() => {});
//            }
//        }
//
//        function buildBar() {
//            if (document.querySelector(".o_sl_filter_bar")) return;
//
//            // ── Find the correct insertion point ──────────────────────
//            // We want to insert INSIDE .o_content, ABOVE .o_list_view
//            // but BELOW .o_control_panel (search bar area)
//            const listView = document.querySelector(".o_list_view");
//            if (!listView) return;
//
//            // Insert the bar as a sibling BEFORE .o_list_view, not inside it
//            const parent = listView.parentElement;
//            if (!parent) return;
//
//            const uid = Date.now();
//
//            const bar = document.createElement("div");
//            bar.className = "o_sl_filter_bar";
//
//            bar.innerHTML = `
//                <div class="slf-wrap">
//
//                    <div class="slf-field" style="flex:2;min-width:160px;position:relative;">
//                        <input id="slf_prod_${uid}" type="text" class="slf-input"
//                            placeholder="Product name or code" autocomplete="off"/>
//                        <div id="slf_ac_${uid}" class="slf-autocomplete" style="display:none;"></div>
//                    </div>
//
//                    <div class="slf-field" style="min-width:120px;">
//                        <select id="slf_wh_${uid}" class="slf-input">
//                            <option value="">Warehouse</option>
//                        </select>
//                    </div>
//
//                    <div class="slf-date-wrap">
//                        <input id="slf_df_${uid}" type="date" class="slf-input slf-date"/>
//                        <span class="slf-arrow">→</span>
//                        <input id="slf_dt_${uid}" type="date" class="slf-input slf-date"/>
//                    </div>
//
//                    <div class="slf-field" style="min-width:110px;">
//                        <input id="slf_vou_${uid}" type="text" class="slf-input"
//                            placeholder="Voucher"/>
//                    </div>
//
//                    <div class="slf-field" style="min-width:90px;">
//                        <select id="slf_type_${uid}" class="slf-input">
//                            <option value="">Type</option>
//                            <option value="IN">IN</option>
//                            <option value="OUT">OUT</option>
//                            <option value="INT">INT</option>
//                        </select>
//                    </div>
//
//                    <div class="slf-field" style="min-width:130px;">
//                        <select id="slf_inv_${uid}" class="slf-input">
//                            <option value="">Invoice Status</option>
//                            <option value="invoiced">Invoiced</option>
//                            <option value="to invoice">To Invoice</option>
//                            <option value="nothing">Nothing</option>
//                        </select>
//                    </div>
//
//                    <div class="slf-actions">
//                        <button id="slf_apply_${uid}" class="slf-btn slf-btn-apply">
//                            Apply <kbd>↵</kbd>
//                        </button>
//                        <button id="slf_clear_${uid}" class="slf-btn slf-btn-clear">
//                            Clear <kbd>Esc</kbd>
//                        </button>
//                    </div>
//
//                </div>
//            `;
//
//            // Insert BEFORE the list view (so it appears between control panel and list)
//            parent.insertBefore(bar, listView);
//
//            // ── Load warehouses ───────────────────────────────────────
//            orm.searchRead("stock.warehouse", [], ["id", "name"], { limit: 200 })
//                .then(rows => {
//                    const sel = document.getElementById(`slf_wh_${uid}`);
//                    if (!sel) return;
//                    rows.forEach(({ id, name }) => {
//                        const opt = document.createElement("option");
//                        opt.value = id;
//                        opt.textContent = name;
//                        sel.appendChild(opt);
//                    });
//                }).catch(() => {});
//
//            // ── Product autocomplete ──────────────────────────────────
//            const prodInput = document.getElementById(`slf_prod_${uid}`);
//            const acBox     = document.getElementById(`slf_ac_${uid}`);
//            let acTimer     = null;
//
//            const hideAc = () => { acBox.style.display = "none"; acBox.innerHTML = ""; };
//
//            prodInput.addEventListener("input", () => {
//                prodInput.removeAttribute("data-pid");
//                const q = prodInput.value.trim();
//                if (!q) { hideAc(); return; }
//                if (acTimer) clearTimeout(acTimer);
//                acBox.innerHTML = `<div class="slf-ac-item" style="color:#999;">Searching…</div>`;
//                acBox.style.display = "block";
//                acTimer = setTimeout(() => {
//                    orm.searchRead(
//                        "product.product",
//                        ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
//                        ["id", "display_name", "default_code"],
//                        { limit: 20, order: "default_code asc, name asc" }
//                    ).then(results => {
//                        acBox.innerHTML = "";
//                        if (!results.length) {
//                            acBox.innerHTML = `<div class="slf-ac-item" style="color:#999;">No results</div>`;
//                            acBox.style.display = "block";
//                            return;
//                        }
//                        results.forEach(p => {
//                            const d = document.createElement("div");
//                            d.className = "slf-ac-item";
//                            const badge = p.default_code
//                                ? `<span class="slf-badge">[${p.default_code}]</span>`
//                                : "";
//                            d.innerHTML = `${badge}<span>${p.display_name || p.name}</span>`;
//                            d.addEventListener("mousedown", e => {
//                                e.preventDefault();
//                                prodInput.value = p.display_name;
//                                prodInput.setAttribute("data-pid", p.id);
//                                hideAc();
//                            });
//                            acBox.appendChild(d);
//                        });
//                        acBox.style.display = "block";
//                    }).catch(() => hideAc());
//                }, 280);
//            });
//
//            prodInput.addEventListener("blur", () => setTimeout(hideAc, 180));
//
//            // ── Apply / Clear logic ───────────────────────────────────
//            const g = id => document.getElementById(id);
//
//            const getDomain = () => {
//                const domain = [];
//                const pi  = g(`slf_prod_${uid}`);
//                const pid = pi && parseInt(pi.getAttribute("data-pid") || "0");
//                if (pid) {
//                    domain.push(["product_id", "=", pid]);
//                } else if (pi && pi.value.trim()) {
//                    domain.push(["product_id.display_name", "ilike", pi.value.trim()]);
//                }
//                const wh = g(`slf_wh_${uid}`);
//                if (wh && wh.value) domain.push(["warehouse_id", "=", parseInt(wh.value)]);
//                const df = g(`slf_df_${uid}`);
//                const dt = g(`slf_dt_${uid}`);
//                if (df && df.value) domain.push(["date", ">=", df.value + " 00:00:00"]);
//                if (dt && dt.value) domain.push(["date", "<=", dt.value + " 23:59:59"]);
//                const vo = g(`slf_vou_${uid}`);
//                if (vo && vo.value.trim()) domain.push(["voucher", "ilike", vo.value.trim()]);
//                const ty = g(`slf_type_${uid}`);
//                if (ty && ty.value) domain.push(["move_type", "=", ty.value]);
//                const iv = g(`slf_inv_${uid}`);
//                if (iv && iv.value) domain.push(["invoice_status", "=", iv.value]);
//                return domain;
//            };
//
//            const doApply = () => applyDomain(getDomain());
//
//            const doClear = () => {
//                ["slf_wh_", "slf_type_", "slf_inv_"].forEach(k => {
//                    const el = g(k + uid); if (el) el.value = "";
//                });
//                ["slf_df_", "slf_dt_", "slf_vou_"].forEach(k => {
//                    const el = g(k + uid); if (el) el.value = "";
//                });
//                const pi = g(`slf_prod_${uid}`);
//                if (pi) { pi.value = ""; pi.removeAttribute("data-pid"); }
//                applyDomain([]);
//            };
//
//            g(`slf_apply_${uid}`).addEventListener("click", doApply);
//            g(`slf_clear_${uid}`).addEventListener("click", doClear);
//
//            // ── Keyboard shortcuts ────────────────────────────────────
//            const onKey = e => {
//                if (document.querySelector(".o_dialog, .modal.show")) return;
//                const active = document.activeElement;
//                const inBar  = bar.contains(active);
//                const inOtherInput = !inBar && (
//                    active.tagName === "INPUT" ||
//                    active.tagName === "TEXTAREA" ||
//                    active.tagName === "SELECT"
//                );
//                if (inOtherInput) return;
//                if (e.key === "Enter")  doApply();
//                if (e.key === "Escape") doClear();
//            };
//            document.addEventListener("keydown", onKey);
//            bar._cleanup = () => document.removeEventListener("keydown", onKey);
//        }
//
//        // ── MutationObserver ──────────────────────────────────────────
//        const observer = new MutationObserver(() => {
//            if (debounce) clearTimeout(debounce);
//            debounce = setTimeout(() => {
//                const existingBar = document.querySelector(".o_sl_filter_bar");
//
//                if (!isStockLedgerView()) {
//                    if (existingBar) {
//                        if (existingBar._cleanup) existingBar._cleanup();
//                        existingBar.remove();
//                    }
//                    return;
//                }
//
//                if (!existingBar && document.querySelector(".o_list_view .o_list_table")) {
//                    buildBar();
//                }
//            }, 400);
//        });
//
//        observer.observe(document.body, { childList: true, subtree: true });
//
//        return {
//            destroy() {
//                observer.disconnect();
//                const bar = document.querySelector(".o_sl_filter_bar");
//                if (bar) {
//                    if (bar._cleanup) bar._cleanup();
//                    bar.remove();
//                }
//            }
//        };
//    }
//});
