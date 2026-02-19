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

        var listTable = document.querySelector(".o_list_table");
        if (!listTable) {
            setTimeout(() => this.injectPsfBar(), 150);
            return;
        }

        var ts = Date.now();

        var bar = document.createElement("div");
        bar.className = "psf_filter_bar";
        bar.innerHTML = [
            '<div class="psf_inner">',
            '  <div class="psf_filters">',

            '    <div class="psf_group psf_product_group" style="position:relative;">',
            '      <input type="text" id="psf_product_' + ts + '" class="psf_input"',
            '             placeholder="Product" autocomplete="off"/>',
            '      <div id="psf_ac_' + ts + '" class="psf_autocomplete" style="display:none;"></div>',
            '    </div>',

            '    <div class="psf_group">',
            '      <select id="psf_stock_' + ts + '" class="psf_select">',
            '        <option value="">Stock</option>',
            '        <option value="zero">Zero Stock</option>',
            '        <option value="negative">Negative Stock</option>',
            '        <option value="positive">In Stock</option>',
            '      </select>',
            '    </div>',

            '    <div class="psf_group psf_gt_group">',
            '      <input type="text" id="psf_gt_' + ts + '" class="psf_input"',
            '             placeholder="On Hand greater than" inputmode="decimal"/>',
            '    </div>',

            '  </div>',
            '  <div class="psf_actions">',
            '    <button id="psf_apply_' + ts + '" class="psf_btn psf_btn_apply" type="button">Apply</button>',
            '    <button id="psf_clear_' + ts + '" class="psf_btn psf_btn_clear" type="button">Clear</button>',
            '  </div>',
            '</div>'
        ].join('');

        listTable.parentElement.insertBefore(bar, listTable);
        this._psfElement = bar;

        var get = function(id) { return document.getElementById(id); };

        var productInput = get("psf_product_" + ts);
        var acBox        = get("psf_ac_" + ts);
        var stockSelect  = get("psf_stock_" + ts);
        var gtInput      = get("psf_gt_" + ts);
        var applyBtn     = get("psf_apply_" + ts);
        var clearBtn     = get("psf_clear_" + ts);

        // Numeric-only validation for gt input
        gtInput.addEventListener("input", function() {
            if (!/^-?\d*\.?\d*$/.test(this.value)) {
                this.value = this.value.slice(0, -1);
            }
        });

        var self = this;

        // Apply domain
        var doApply = function() {
            var domain = [];

            var pid = parseInt(productInput.getAttribute("data-product-id") || "0");
            var ptxt = productInput.value.trim();
            if (pid) {
                domain.push(["id", "=", pid]);
            } else if (ptxt) {
                domain.push("|");
                domain.push(["name", "ilike", ptxt]);
                domain.push(["default_code", "ilike", ptxt]);
            }

            var sv = stockSelect.value;
            if (sv === "zero")     domain.push(["qty_available", "=", 0]);
            if (sv === "negative") domain.push(["qty_available", "<", 0]);
            if (sv === "positive") domain.push(["qty_available", ">", 0]);

            var gt = parseFloat(gtInput.value);
            if (gtInput.value.trim() && !isNaN(gt)) {
                domain.push(["qty_available", ">", gt]);
            }

            if (self.model && self.model.load) {
                self.model.load({ domain: domain }).catch(function(err) {
                    console.warn("PSF apply error:", err);
                });
                self.notification.add("Filters applied", { type: "success" });
            }
        };

        // Clear
        var doClear = function() {
            productInput.value = "";
            productInput.removeAttribute("data-product-id");
            acBox.style.display = "none";
            acBox.innerHTML = "";
            stockSelect.value = "";
            gtInput.value = "";

            if (self.model && self.model.load) {
                self.model.load({ domain: [] }).catch(function(err) {
                    console.warn("PSF clear error:", err);
                });
                self.notification.add("Filters cleared", { type: "info" });
            }
        };

        applyBtn.addEventListener("click", doApply);
        clearBtn.addEventListener("click", doClear);

        // Keyboard shortcuts
        this._psfKeyHandler = function(e) {
            if (e.key === "Enter") {
                var acOpen = acBox.style.display !== "none";
                var acActive = acBox.querySelector(".psf_ac_item.active");
                if (acOpen && acActive) return;
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

        // Autocomplete
        var showAc = function(products) {
            acBox.innerHTML = "";
            if (!products.length) { acBox.style.display = "none"; return; }
            products.forEach(function(p) {
                var item = document.createElement("div");
                item.className = "psf_ac_item";
                item.setAttribute("data-id", p.id);
                item.setAttribute("data-name", p.display_name);
                var badge = p.default_code
                    ? '<span class="psf_ac_badge">' + p.default_code + '</span>'
                    : '';
                item.innerHTML = badge + '<span class="psf_ac_name">' + p.display_name + '</span>';
                item.addEventListener("mousedown", function(ev) {
                    ev.preventDefault();
                    productInput.value = p.display_name;
                    productInput.setAttribute("data-product-id", p.id);
                    acBox.style.display = "none";
                });
                acBox.appendChild(item);
            });
            acBox.style.display = "block";
        };

        productInput.addEventListener("input", function() {
            productInput.removeAttribute("data-product-id");
            var q = productInput.value.trim();
            clearTimeout(self._psfDebounce);
            if (!q) { acBox.style.display = "none"; acBox.innerHTML = ""; return; }
            self._psfDebounce = setTimeout(function() {
                self.orm.searchRead(
                    "product.template",
                    ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
                    ["id", "display_name", "default_code"],
                    { limit: 10 }
                ).then(function(results) {
                    showAc(results);
                }).catch(function(err) {
                    console.warn("PSF autocomplete error:", err);
                });
            }, 280);
        });

        productInput.addEventListener("keydown", function(e) {
            if (acBox.style.display === "none") return;
            var items = acBox.querySelectorAll(".psf_ac_item");
            if (!items.length) return;
            var active = acBox.querySelector(".psf_ac_item.active");
            var idx = Array.from(items).indexOf(active);

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

        acBox.addEventListener("mouseleave", function() {
            acBox.querySelectorAll(".psf_ac_item.active").forEach(function(el) {
                el.classList.remove("active");
            });
        });

        this._psfClickOutside = function(e) {
            if (!productInput.contains(e.target) && !acBox.contains(e.target)) {
                acBox.style.display = "none";
            }
        };
        document.addEventListener("mousedown", this._psfClickOutside);
    },
});
