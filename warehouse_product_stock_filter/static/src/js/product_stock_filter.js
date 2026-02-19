/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {

    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this._stockFilterElement = null;
        this._stockFilterKeyHandler = null;
        this._stockFilterClickOutside = null;

        onMounted(() => {
            if (this._shouldShowStockFilter()) {
                setTimeout(() => this._injectStockFilterBar(), 200);
            }
        });

        onWillUnmount(() => {
            this._cleanupStockFilter();
        });
    },

    // ── Guard: only show on product.template list ────────────────────────
    _shouldShowStockFilter() {
        return this.props.resModel === "product.template";
    },

    // ── Cleanup ──────────────────────────────────────────────────────────
    _cleanupStockFilter() {
        if (this._stockFilterElement && this._stockFilterElement.parentNode) {
            this._stockFilterElement.remove();
            this._stockFilterElement = null;
        }
        if (this._stockFilterKeyHandler) {
            document.removeEventListener("keydown", this._stockFilterKeyHandler);
            this._stockFilterKeyHandler = null;
        }
        if (this._stockFilterClickOutside) {
            document.removeEventListener("mousedown", this._stockFilterClickOutside);
            this._stockFilterClickOutside = null;
        }
    },

    // ── Inject filter bar above the list table ───────────────────────────
    _injectStockFilterBar() {
        this._cleanupStockFilter();

        // Already injected?
        if (document.querySelector(".psf_filter_bar")) return;

        // Find the list table container
        const listTable = document.querySelector(".o_list_table");
        if (!listTable) {
            setTimeout(() => this._injectStockFilterBar(), 150);
            return;
        }

        const ts = Date.now();

        const bar = document.createElement("div");
        bar.className = "psf_filter_bar";
        bar.innerHTML = this._buildFilterBarHTML(ts);

        listTable.parentElement.insertBefore(bar, listTable);
        this._stockFilterElement = bar;

        this._attachFilterEvents(ts);
    },

    // ── HTML builder ─────────────────────────────────────────────────────
    _buildFilterBarHTML(ts) {
        return `
        <div class="psf_inner">
            <div class="psf_filters">

                <!-- 1. Product search with autocomplete -->
                <div class="psf_group psf_product_group" style="position:relative;">
                    <label class="psf_label">Product</label>
                    <input
                        type="text"
                        id="psf_product_${ts}"
                        class="psf_input"
                        placeholder="Name or code…"
                        autocomplete="off"
                    />
                    <div id="psf_autocomplete_${ts}" class="psf_autocomplete" style="display:none;"></div>
                </div>

                <!-- 2. Stock type dropdown -->
                <div class="psf_group">
                    <label class="psf_label">Stock</label>
                    <select id="psf_stock_${ts}" class="psf_select">
                        <option value="">All</option>
                        <option value="zero">Zero Stock</option>
                        <option value="negative">Negative Stock</option>
                        <option value="positive">In Stock</option>
                    </select>
                </div>

                <!-- 3. Greater than -->
                <div class="psf_group psf_gt_group">
                    <label class="psf_label">On Hand &gt;</label>
                    <input
                        type="text"
                        id="psf_gt_${ts}"
                        class="psf_input psf_input_sm"
                        placeholder="e.g. 10"
                        inputmode="decimal"
                    />
                </div>

                <!-- 4. Product type -->
                <div class="psf_group">
                    <label class="psf_label">Type</label>
                    <select id="psf_type_${ts}" class="psf_select">
                        <option value="">All Types</option>
                        <option value="consu">Consumable</option>
                        <option value="storable">Storable</option>
                        <option value="service">Service</option>
                    </select>
                </div>

                <!-- 5. Sales price range -->
                <div class="psf_group psf_range_group">
                    <label class="psf_label">Sales Price</label>
                    <div class="psf_range_inputs">
                        <input type="text" id="psf_price_from_${ts}" class="psf_input psf_input_sm" placeholder="Min" inputmode="decimal"/>
                        <span class="psf_range_sep">→</span>
                        <input type="text" id="psf_price_to_${ts}" class="psf_input psf_input_sm" placeholder="Max" inputmode="decimal"/>
                    </div>
                </div>

            </div>

            <!-- Action buttons -->
            <div class="psf_actions">
                <button id="psf_apply_${ts}" class="psf_btn psf_btn_apply" title="Apply filters [Enter]">
                    <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 4h18M7 10h10M11 16h2"/></svg>
                    Apply
                </button>
                <button id="psf_clear_${ts}" class="psf_btn psf_btn_clear" title="Clear filters [Esc]">
                    <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
                    Clear
                </button>
            </div>
        </div>`;
    },

    // ── Attach all events ────────────────────────────────────────────────
    _attachFilterEvents(ts) {
        const get = (id) => document.getElementById(id);

        const productInput   = get(`psf_product_${ts}`);
        const autocomplete   = get(`psf_autocomplete_${ts}`);
        const stockSelect    = get(`psf_stock_${ts}`);
        const gtInput        = get(`psf_gt_${ts}`);
        const typeSelect     = get(`psf_type_${ts}`);
        const priceFromInput = get(`psf_price_from_${ts}`);
        const priceToInput   = get(`psf_price_to_${ts}`);
        const applyBtn       = get(`psf_apply_${ts}`);
        const clearBtn       = get(`psf_clear_${ts}`);

        if (!applyBtn) return;

        // ── Numeric-only inputs ──────────────────────────────────────────
        [gtInput, priceFromInput, priceToInput].forEach(inp => {
            if (!inp) return;
            inp.addEventListener("input", (e) => {
                if (!/^-?\d*\.?\d*$/.test(e.target.value)) {
                    e.target.value = e.target.value.slice(0, -1);
                }
            });
        });

        // ── Product autocomplete ─────────────────────────────────────────
        this._setupProductAutocomplete(productInput, autocomplete, ts);

        // ── Apply ────────────────────────────────────────────────────────
        const doApply = () => {
            const domain = [];

            // Product
            const productId = parseInt(productInput?.getAttribute("data-product-id") || "0");
            const productText = productInput?.value.trim() || "";
            if (productId) {
                domain.push(["id", "=", productId]);
            } else if (productText) {
                domain.push(["|",
                    ["name", "ilike", productText],
                    ["default_code", "ilike", productText]
                ]);
            }

            // Stock
            const stockVal = stockSelect?.value || "";
            if (stockVal === "zero")     domain.push(["qty_available", "=", 0]);
            if (stockVal === "negative") domain.push(["qty_available", "<", 0]);
            if (stockVal === "positive") domain.push(["qty_available", ">", 0]);

            // Greater than
            const gt = parseFloat(gtInput?.value || "");
            if (!isNaN(gt) && gtInput?.value.trim()) {
                domain.push(["qty_available", ">", gt]);
            }

            // Product type
            const typeVal = typeSelect?.value || "";
            if (typeVal) domain.push(["type", "=", typeVal]);

            // Price range
            const priceFrom = parseFloat(priceFromInput?.value || "");
            const priceTo   = parseFloat(priceToInput?.value || "");
            if (!isNaN(priceFrom) && priceFromInput?.value.trim()) {
                domain.push(["list_price", ">=", priceFrom]);
            }
            if (!isNaN(priceTo) && priceToInput?.value.trim()) {
                domain.push(["list_price", "<=", priceTo]);
            }

            // Validate price range
            if (!isNaN(priceFrom) && !isNaN(priceTo) && priceFrom > priceTo) {
                this.notification.add("Price From must be less than or equal to Price To", { type: "warning" });
                return;
            }

            if (this.model?.load) {
                this.model.load({ domain }).catch(e => console.warn("Filter load:", e));
                this.notification.add("Filters applied", { type: "success" });
            }
        };

        // ── Clear ────────────────────────────────────────────────────────
        const doClear = () => {
            if (productInput) {
                productInput.value = "";
                productInput.removeAttribute("data-product-id");
            }
            if (autocomplete) { autocomplete.style.display = "none"; autocomplete.innerHTML = ""; }
            if (stockSelect)    stockSelect.value = "";
            if (gtInput)        gtInput.value = "";
            if (typeSelect)     typeSelect.value = "";
            if (priceFromInput) priceFromInput.value = "";
            if (priceToInput)   priceToInput.value = "";

            if (this.model?.load) {
                this.model.load({ domain: [] }).catch(e => console.warn("Clear load:", e));
                this.notification.add("Filters cleared", { type: "info" });
            }
        };

        applyBtn.addEventListener("click", doApply);
        clearBtn.addEventListener("click", doClear);

        // ── Keyboard shortcuts ───────────────────────────────────────────
        this._stockFilterKeyHandler = (e) => {
            const focused = document.activeElement;
            // Enter: apply (but not if product autocomplete is open and active item selected)
            if (e.key === "Enter") {
                const hasActiveAutocomplete = autocomplete &&
                    autocomplete.style.display !== "none" &&
                    autocomplete.querySelector(".psf_ac_item.active");
                if (!hasActiveAutocomplete) {
                    e.preventDefault();
                    doApply();
                }
            }
            // Esc: clear
            if (e.key === "Escape") {
                if (autocomplete && autocomplete.style.display !== "none") {
                    autocomplete.style.display = "none";
                } else {
                    doClear();
                }
            }
        };
        document.addEventListener("keydown", this._stockFilterKeyHandler);
    },

    // ── Product autocomplete ─────────────────────────────────────────────
    _setupProductAutocomplete(input, dropdown, ts) {
        if (!input || !dropdown) return;

        let debounceTimer = null;

        const showDropdown = (items) => {
            dropdown.innerHTML = "";
            if (!items.length) { dropdown.style.display = "none"; return; }
            items.forEach(p => {
                const item = document.createElement("div");
                item.className = "psf_ac_item";
                item.setAttribute("data-id", p.id);
                item.setAttribute("data-name", p.display_name);
                item.innerHTML = `
                    ${p.default_code ? `<span class="psf_ac_badge">${p.default_code}</span>` : ""}
                    <span class="psf_ac_name">${p.display_name}</span>
                `;
                item.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    input.value = p.display_name;
                    input.setAttribute("data-product-id", p.id);
                    dropdown.style.display = "none";
                });
                dropdown.appendChild(item);
            });
            dropdown.style.display = "block";
        };

        const hideDropdown = () => {
            dropdown.style.display = "none";
        };

        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            input.removeAttribute("data-product-id");
            const q = input.value.trim();
            if (!q) { hideDropdown(); return; }
            debounceTimer = setTimeout(async () => {
                try {
                    const results = await this.orm.searchRead(
                        "product.template",
                        ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
                        ["id", "display_name", "default_code"],
                        { limit: 10 }
                    );
                    showDropdown(results);
                } catch (e) {
                    console.warn("Autocomplete error:", e);
                }
            }, 250);
        });

        input.addEventListener("keydown", (e) => {
            if (dropdown.style.display === "none") return;
            const items = dropdown.querySelectorAll(".psf_ac_item");
            if (!items.length) return;
            const active = dropdown.querySelector(".psf_ac_item.active");
            let idx = Array.from(items).indexOf(active);

            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (active) active.classList.remove("active");
                idx = (idx + 1) % items.length;
                items[idx].classList.add("active");
                items[idx].scrollIntoView({ block: "nearest" });
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (active) active.classList.remove("active");
                idx = (idx - 1 + items.length) % items.length;
                items[idx].classList.add("active");
                items[idx].scrollIntoView({ block: "nearest" });
            } else if (e.key === "Enter" && active) {
                e.preventDefault();
                e.stopPropagation();
                const id = active.getAttribute("data-id");
                const name = active.getAttribute("data-name");
                input.value = name;
                input.setAttribute("data-product-id", id);
                hideDropdown();
            } else if (e.key === "Escape") {
                hideDropdown();
            }
        });

        // Click outside closes dropdown
        this._stockFilterClickOutside = (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                hideDropdown();
            }
        };
        document.addEventListener("mousedown", this._stockFilterClickOutside);

        dropdown.addEventListener("mouseleave", () => {
            dropdown.querySelectorAll(".psf_ac_item.active").forEach(el => el.classList.remove("active"));
        });
    },
});
