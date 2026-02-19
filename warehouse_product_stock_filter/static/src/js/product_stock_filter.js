/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {

    setup() {
        super.setup(...arguments);

        this.notification = useService("notification");
        this.orm = useService("orm");

        this._psfElement = null;
        this._psfKeyHandler = null;
        this._psfClickOutside = null;
        this._psfDebounce = null;

        onMounted(() => {
            if (this.props.resModel === "product.template") {
                setTimeout(() => this.injectPsfBar(), 200);
            }
        });

        onWillUnmount(() => {
            this.cleanupPsfBar();
        });
    },

    cleanupPsfBar() {
        if (this._psfElement && this._psfElement.parentNode) {
            this._psfElement.remove();
            this._psfElement = null;
        }
        if (this._psfKeyHandler) {
            document.removeEventListener("keydown", this._psfKeyHandler);
            this._psfKeyHandler = null;
        }
        if (this._psfClickOutside) {
            document.removeEventListener("mousedown", this._psfClickOutside);
            this._psfClickOutside = null;
        }
        if (this._psfDebounce) {
            clearTimeout(this._psfDebounce);
            this._psfDebounce = null;
        }
    },

    injectPsfBar() {
        this.cleanupPsfBar();

        if (document.querySelector(".psf_filter_bar")) return;

        const listTable = document.querySelector(".o_list_table");
        if (!listTable) {
            setTimeout(() => this.injectPsfBar(), 150);
            return;
        }

        const ts = Date.now();

        const bar = document.createElement("div");
        bar.className = "psf_filter_bar";
        bar.innerHTML = `
            <div class="psf_inner">
                <div class="psf_filters">

                    <div class="psf_group psf_product_group" style="position:relative;">
                        <label class="psf_label">Product</label>
                        <input type="text" id="psf_product_${ts}" class="psf_input"
                               placeholder="Name or internal ref…" autocomplete="off"/>
                        <div id="psf_ac_${ts}" class="psf_autocomplete" style="display:none;"></div>
                    </div>

                    <div class="psf_group">
                        <label class="psf_label">Stock</label>
                        <select id="psf_stock_${ts}" class="psf_select">
                            <option value="">All</option>
                            <option value="zero">Zero Stock</option>
                            <option value="negative">Negative Stock</option>
                            <option value="positive">In Stock</option>
                        </select>
                    </div>

                    <div class="psf_group psf_gt_group">
                        <label class="psf_label">On Hand &gt;</label>
                        <input type="text" id="psf_gt_${ts}" class="psf_input"
                               placeholder="e.g. 10" inputmode="decimal"/>
                    </div>

                    <div class="psf_group">
                        <label class="psf_label">Type</label>
                        <select id="psf_type_${ts}" class="psf_select">
                            <option value="">All Types</option>
                            <option value="consu">Consumable</option>
                            <option value="storable">Storable</option>
                            <option value="service">Service</option>
                        </select>
                    </div>

                    <div class="psf_group psf_range_group">
                        <label class="psf_label">Sales Price</label>
                        <div class="psf_range_inputs">
                            <input type="text" id="psf_pfrom_${ts}" class="psf_input" placeholder="Min" inputmode="decimal"/>
                            <span class="psf_range_sep">&#8594;</span>
                            <input type="text" id="psf_pto_${ts}" class="psf_input" placeholder="Max" inputmode="decimal"/>
                        </div>
                    </div>

                </div>
                <div class="psf_actions">
                    <button id="psf_apply_${ts}" class="psf_btn psf_btn_apply" type="button">
                        &#9663; Apply
                    </button>
                    <button id="psf_clear_${ts}" class="psf_btn psf_btn_clear" type="button">
                        &#x2715; Clear
                    </button>
                </div>
            </div>
        `;

        listTable.parentElement.insertBefore(bar, listTable);
        this._psfElement = bar;

        // ── Get all inputs ───────────────────────────────────────────────
        const productInput = document.getElementById(`psf_product_${ts}`);
        const acBox        = document.getElementById(`psf_ac_${ts}`);
        const stockSelect  = document.getElementById(`psf_stock_${ts}`);
        const gtInput      = document.getElementById(`psf_gt_${ts}`);
        const typeSelect   = document.getElementById(`psf_type_${ts}`);
        const priceFrom    = document.getElementById(`psf_pfrom_${ts}`);
        const priceTo      = document.getElementById(`psf_pto_${ts}`);
        const applyBtn     = document.getElementById(`psf_apply_${ts}`);
        const clearBtn     = document.getElementById(`psf_clear_${ts}`);

        // ── Numeric validation ───────────────────────────────────────────
        [gtInput, priceFrom, priceTo].forEach(inp => {
            if (!inp) return;
            inp.addEventListener("input", function() {
                if (!/^-?\d*\.?\d*$/.test(this.value)) {
                    this.value = this.value.slice(0, -1);
                }
            });
        });

        // ── Apply domain ─────────────────────────────────────────────────
        const doApply = () => {
            const domain = [];

            // Product
            const pid = parseInt(productInput.getAttribute("data-product-id") || "0");
            const ptxt = productInput.value.trim();
            if (pid) {
                domain.push(["id", "=", pid]);
            } else if (ptxt) {
                domain.push("|");
                domain.push(["name", "ilike", ptxt]);
                domain.push(["default_code", "ilike", ptxt]);
            }

            // Stock status
            const sv = stockSelect.value;
            if (sv === "zero")     domain.push(["qty_available", "=", 0]);
            if (sv === "negative") domain.push(["qty_available", "<", 0]);
            if (sv === "positive") domain.push(["qty_available", ">", 0]);

            // On hand greater than
            const gt = parseFloat(gtInput.value);
            if (gtInput.value.trim() && !isNaN(gt)) {
                domain.push(["qty_available", ">", gt]);
            }

            // Product type
            if (typeSelect.value) {
                domain.push(["type", "=", typeSelect.value]);
            }

            // Price range
            const pf = parseFloat(priceFrom.value);
            const pt = parseFloat(priceTo.value);
            if (priceFrom.value.trim() && !isNaN(pf)) domain.push(["list_price", ">=", pf]);
            if (priceTo.value.trim() && !isNaN(pt))   domain.push(["list_price", "<=", pt]);

            if (priceFrom.value.trim() && priceTo.value.trim() && !isNaN(pf) && !isNaN(pt) && pf > pt) {
                this.notification.add("Price Min must be ≤ Price Max", { type: "warning" });
                return;
            }

            if (this.model && this.model.load) {
                this.model.load({ domain: domain }).catch(err => {
                    console.warn("PSF apply error:", err);
                });
                this.notification.add("Filters applied", { type: "success" });
            }
        };

        // ── Clear ────────────────────────────────────────────────────────
        const doClear = () => {
            productInput.value = "";
            productInput.removeAttribute("data-product-id");
            acBox.style.display = "none";
            acBox.innerHTML = "";
            stockSelect.value = "";
            gtInput.value = "";
            typeSelect.value = "";
            priceFrom.value = "";
            priceTo.value = "";

            if (this.model && this.model.load) {
                this.model.load({ domain: [] }).catch(err => {
                    console.warn("PSF clear error:", err);
                });
                this.notification.add("Filters cleared", { type: "info" });
            }
        };

        applyBtn.addEventListener("click", doApply);
        clearBtn.addEventListener("click", doClear);

        // ── Keyboard shortcuts ───────────────────────────────────────────
        this._psfKeyHandler = (e) => {
            if (e.key === "Enter") {
                const acOpen = acBox.style.display !== "none";
                const acActive = acBox.querySelector(".psf_ac_item.active");
                if (acOpen && acActive) return; // let autocomplete handle it
                e.preventDefault();
                doApply();
            }
            if (e.key === "Escape") {
                if (acBox.style.display !== "none") {
                    acBox.style.display = "none";
                } else {
                    doClear();
                }
            }
        };
        document.addEventListener("keydown", this._psfKeyHandler);

        // ── Product autocomplete ─────────────────────────────────────────
        const showAc = (products) => {
            acBox.innerHTML = "";
            if (!products.length) { acBox.style.display = "none"; return; }
            products.forEach(p => {
                const item = document.createElement("div");
                item.className = "psf_ac_item";
                item.setAttribute("data-id", p.id);
                item.setAttribute("data-name", p.display_name);
                item.innerHTML =
                    (p.default_code ? `<span class="psf_ac_badge">${p.default_code}</span>` : "") +
                    `<span class="psf_ac_name">${p.display_name}</span>`;
                item.addEventListener("mousedown", (ev) => {
                    ev.preventDefault();
                    productInput.value = p.display_name;
                    productInput.setAttribute("data-product-id", p.id);
                    acBox.style.display = "none";
                });
                acBox.appendChild(item);
            });
            acBox.style.display = "block";
        };

        productInput.addEventListener("input", () => {
            productInput.removeAttribute("data-product-id");
            const q = productInput.value.trim();
            clearTimeout(this._psfDebounce);
            if (!q) { acBox.style.display = "none"; acBox.innerHTML = ""; return; }
            this._psfDebounce = setTimeout(async () => {
                try {
                    const results = await this.orm.searchRead(
                        "product.template",
                        ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
                        ["id", "display_name", "default_code"],
                        { limit: 10 }
                    );
                    showAc(results);
                } catch (err) {
                    console.warn("PSF autocomplete error:", err);
                }
            }, 280);
        });

        productInput.addEventListener("keydown", (e) => {
            if (acBox.style.display === "none") return;
            const items = acBox.querySelectorAll(".psf_ac_item");
            if (!items.length) return;
            const active = acBox.querySelector(".psf_ac_item.active");
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
                productInput.value = active.getAttribute("data-name");
                productInput.setAttribute("data-product-id", active.getAttribute("data-id"));
                acBox.style.display = "none";
            } else if (e.key === "Escape") {
                acBox.style.display = "none";
            }
        });

        acBox.addEventListener("mouseleave", () => {
            acBox.querySelectorAll(".psf_ac_item.active").forEach(el => el.classList.remove("active"));
        });

        this._psfClickOutside = (e) => {
            if (!productInput.contains(e.target) && !acBox.contains(e.target)) {
                acBox.style.display = "none";
            }
        };
        document.addEventListener("mousedown", this._psfClickOutside);
    },
});