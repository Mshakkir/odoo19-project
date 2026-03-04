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

    // Parse dd/mm/yy or dd/mm/yyyy -> { display: "dd/mm/yy", iso: "YYYY-MM-DD" } or null
    _psfParseDate(val) {
        val = (val || "").trim();
        if (!val) return null;
        var m = val.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
        if (!m) return null;
        var day   = m[1].padStart(2, "0");
        var month = m[2].padStart(2, "0");
        var year  = m[3].length === 2 ? "20" + m[3] : m[3];
        var d = new Date(year + "-" + month + "-" + day);
        if (isNaN(d.getTime())) return null;
        var yy = year.slice(2);
        return {
            display: day + "/" + month + "/" + yy,   // dd/mm/yy  (matches x_created_date_display)
            iso: year + "-" + month + "-" + day       // YYYY-MM-DD (for native input)
        };
    },

    // Mask dd/mm/yy on text input and keep hidden native date input in sync
    _psfDateMask(textInput, hiddenInput) {
        textInput.addEventListener("input", function() {
            var v = textInput.value.replace(/[^\d]/g, "");
            var out = "";
            if (v.length > 0) out += v.substring(0, 2);
            if (v.length >= 3) out += "/" + v.substring(2, 4);
            if (v.length >= 5) out += "/" + v.substring(4, 6);
            textInput.value = out;
            // Sync hidden native picker
            if (out.length === 8) {
                var p = out.split("/");
                if (p.length === 3) {
                    hiddenInput.value = "20" + p[2] + "-" + p[1] + "-" + p[0];
                }
            } else {
                hiddenInput.value = "";
            }
        });
        textInput.addEventListener("keydown", function(e) {
            if (e.key === "Backspace" && textInput.value.slice(-1) === "/") {
                textInput.value = textInput.value.slice(0, -1);
                e.preventDefault();
            }
        });
        // When user picks from calendar, update text input
        hiddenInput.addEventListener("change", function() {
            if (hiddenInput.value) {
                var p = hiddenInput.value.split("-");
                // p = [YYYY, MM, DD]
                textInput.value = p[2] + "/" + p[1] + "/" + p[0].slice(2);
            } else {
                textInput.value = "";
            }
        });
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

            // --- Date From ---
            '    <div class="psf_group psf_date_group">',
            '      <div class="psf_date_wrap">',
            '        <input type="text" id="psf_date_from_txt_' + ts + '" class="psf_input psf_date_input"',
            '               placeholder="Date From (dd/mm/yy)" maxlength="8" autocomplete="off"/>',
            '        <input type="date" id="psf_date_from_nat_' + ts + '" class="psf_date_native" tabindex="-1"/>',
            '        <button type="button" class="psf_cal_btn" id="psf_cal_from_' + ts + '" title="Choose date">',
            '          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"',
            '               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
            '            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>',
            '            <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>',
            '            <line x1="3" y1="10" x2="21" y2="10"/>',
            '          </svg>',
            '        </button>',
            '      </div>',
            '    </div>',

            // --- Date To ---
            '    <div class="psf_group psf_date_group">',
            '      <div class="psf_date_wrap">',
            '        <input type="text" id="psf_date_to_txt_' + ts + '" class="psf_input psf_date_input"',
            '               placeholder="Date To (dd/mm/yy)" maxlength="8" autocomplete="off"/>',
            '        <input type="date" id="psf_date_to_nat_' + ts + '" class="psf_date_native" tabindex="-1"/>',
            '        <button type="button" class="psf_cal_btn" id="psf_cal_to_' + ts + '" title="Choose date">',
            '          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"',
            '               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
            '            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>',
            '            <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>',
            '            <line x1="3" y1="10" x2="21" y2="10"/>',
            '          </svg>',
            '        </button>',
            '      </div>',
            '    </div>',

            // --- Product ---
            '    <div class="psf_group psf_product_group" style="position:relative;">',
            '      <input type="text" id="psf_product_' + ts + '" class="psf_input"',
            '             placeholder="Product" autocomplete="off"/>',
            '      <div id="psf_ac_' + ts + '" class="psf_autocomplete" style="display:none;"></div>',
            '    </div>',

            // --- Stock Status ---
            '    <div class="psf_group">',
            '      <select id="psf_stock_' + ts + '" class="psf_select">',
            '        <option value="">Stock</option>',
            '        <option value="zero">Zero Stock</option>',
            '        <option value="negative">Negative Stock</option>',
            '        <option value="positive">In Stock</option>',
            '      </select>',
            '    </div>',

            // --- On Hand Greater Than ---
            '    <div class="psf_group psf_gt_group">',
            '      <input type="text" id="psf_gt_' + ts + '" class="psf_input"',
            '             placeholder="On Hand greater than" inputmode="decimal"/>',
            '    </div>',

            // --- On Hand Less Than ---
            '    <div class="psf_group psf_gt_group">',
            '      <input type="text" id="psf_lt_' + ts + '" class="psf_input"',
            '             placeholder="On Hand less than" inputmode="decimal"/>',
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

        var dateFromTxt  = get("psf_date_from_txt_" + ts);
        var dateFromNat  = get("psf_date_from_nat_" + ts);
        var calFromBtn   = get("psf_cal_from_" + ts);
        var dateToTxt    = get("psf_date_to_txt_" + ts);
        var dateToNat    = get("psf_date_to_nat_" + ts);
        var calToBtn     = get("psf_cal_to_" + ts);
        var productInput = get("psf_product_" + ts);
        var acBox        = get("psf_ac_" + ts);
        var stockSelect  = get("psf_stock_" + ts);
        var gtInput      = get("psf_gt_" + ts);
        var ltInput      = get("psf_lt_" + ts);
        var applyBtn     = get("psf_apply_" + ts);
        var clearBtn     = get("psf_clear_" + ts);

        // Wire up masks + calendar sync
        this._psfDateMask(dateFromTxt, dateFromNat);
        this._psfDateMask(dateToTxt,   dateToNat);

        // Calendar button opens native date picker
        calFromBtn.addEventListener("click", function() {
            try { dateFromNat.showPicker(); } catch(e) { dateFromNat.click(); }
        });
        calToBtn.addEventListener("click", function() {
            try { dateToNat.showPicker(); } catch(e) { dateToNat.click(); }
        });

        // Numeric-only for qty inputs
        function numericOnly(el) {
            el.addEventListener("input", function() {
                if (!/^-?\d*\.?\d*$/.test(this.value)) this.value = this.value.slice(0, -1);
            });
        }
        numericOnly(gtInput);
        numericOnly(ltInput);

        var self = this;

        var doApply = function() {
            var domain = [];
            var errors = [];

            // Date From -> filter on x_created_date_display >= "dd/mm/yy"
            var dfTxt = dateFromTxt.value.trim();
            if (dfTxt) {
                var dfParsed = self._psfParseDate(dfTxt);
                if (!dfParsed) {
                    errors.push("Invalid 'Date From'. Use dd/mm/yy.");
                } else {
                    domain.push(["x_created_date_display", ">=", dfParsed.display]);
                }
            }

            // Date To -> filter on x_created_date_display <= "dd/mm/yy"
            var dtTxt = dateToTxt.value.trim();
            if (dtTxt) {
                var dtParsed = self._psfParseDate(dtTxt);
                if (!dtParsed) {
                    errors.push("Invalid 'Date To'. Use dd/mm/yy.");
                } else {
                    domain.push(["x_created_date_display", "<=", dtParsed.display]);
                }
            }

            if (errors.length) {
                self.notification.add(errors.join(" "), { type: "danger" });
                return;
            }

            // Product
            var pid = parseInt(productInput.getAttribute("data-product-id") || "0");
            var ptxt = productInput.value.trim();
            if (pid) {
                domain.push(["id", "=", pid]);
            } else if (ptxt) {
                domain.push("|");
                domain.push(["name", "ilike", ptxt]);
                domain.push(["default_code", "ilike", ptxt]);
            }

            // Stock status
            var sv = stockSelect.value;
            if (sv === "zero")     domain.push(["qty_available", "=", 0]);
            if (sv === "negative") domain.push(["qty_available", "<", 0]);
            if (sv === "positive") domain.push(["qty_available", ">", 0]);

            // On Hand greater than
            var gt = parseFloat(gtInput.value);
            if (gtInput.value.trim() && !isNaN(gt)) domain.push(["qty_available", ">", gt]);

            // On Hand less than
            var lt = parseFloat(ltInput.value);
            if (ltInput.value.trim() && !isNaN(lt)) domain.push(["qty_available", "<", lt]);

            if (self.model && self.model.load) {
                self.model.load({ domain: domain }).catch(function(err) {
                    console.warn("PSF apply error:", err);
                });
                self.notification.add("Filters applied", { type: "success" });
            }
        };

        var doClear = function() {
            dateFromTxt.value = ""; dateFromNat.value = "";
            dateToTxt.value   = ""; dateToNat.value   = "";
            productInput.value = "";
            productInput.removeAttribute("data-product-id");
            acBox.style.display = "none";
            acBox.innerHTML = "";
            stockSelect.value = "";
            gtInput.value = "";
            ltInput.value = "";

            if (self.model && self.model.load) {
                self.model.load({ domain: [] }).catch(function(err) {
                    console.warn("PSF clear error:", err);
                });
                self.notification.add("Filters cleared", { type: "info" });
            }
        };

        applyBtn.addEventListener("click", doApply);
        clearBtn.addEventListener("click", doClear);

        this._psfKeyHandler = function(e) {
            if (e.key === "Enter") {
                var acOpen   = acBox.style.display !== "none";
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









///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { ListController } from "@web/views/list/list_controller";
//import { onMounted, onWillUnmount } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//
//patch(ListController.prototype, {
//
//    setup() {
//        super.setup(...arguments);
//
//        this.notification = useService("notification");
//        this.orm = useService("orm");
//
//        this._psfElement = null;
//        this._psfKeyHandler = null;
//        this._psfClickOutside = null;
//        this._psfDebounce = null;
//
//        onMounted(() => {
//            if (this.props.resModel === "product.template") {
//                setTimeout(() => this.injectPsfBar(), 200);
//            }
//        });
//
//        onWillUnmount(() => {
//            this.cleanupPsfBar();
//        });
//    },
//
//    cleanupPsfBar() {
//        if (this._psfElement && this._psfElement.parentNode) {
//            this._psfElement.remove();
//            this._psfElement = null;
//        }
//        if (this._psfKeyHandler) {
//            document.removeEventListener("keydown", this._psfKeyHandler);
//            this._psfKeyHandler = null;
//        }
//        if (this._psfClickOutside) {
//            document.removeEventListener("mousedown", this._psfClickOutside);
//            this._psfClickOutside = null;
//        }
//        if (this._psfDebounce) {
//            clearTimeout(this._psfDebounce);
//            this._psfDebounce = null;
//        }
//    },
//
//    injectPsfBar() {
//        this.cleanupPsfBar();
//
//        if (document.querySelector(".psf_filter_bar")) return;
//
//        var listTable = document.querySelector(".o_list_table");
//        if (!listTable) {
//            setTimeout(() => this.injectPsfBar(), 150);
//            return;
//        }
//
//        var ts = Date.now();
//
//        var bar = document.createElement("div");
//        bar.className = "psf_filter_bar";
//        bar.innerHTML = [
//            '<div class="psf_inner">',
//            '  <div class="psf_filters">',
//
//            '    <div class="psf_group psf_product_group" style="position:relative;">',
//            '      <input type="text" id="psf_product_' + ts + '" class="psf_input"',
//            '             placeholder="Product" autocomplete="off"/>',
//            '      <div id="psf_ac_' + ts + '" class="psf_autocomplete" style="display:none;"></div>',
//            '    </div>',
//
//            '    <div class="psf_group">',
//            '      <select id="psf_stock_' + ts + '" class="psf_select">',
//            '        <option value="">Stock</option>',
//            '        <option value="zero">Zero Stock</option>',
//            '        <option value="negative">Negative Stock</option>',
//            '        <option value="positive">In Stock</option>',
//            '      </select>',
//            '    </div>',
//
//            '    <div class="psf_group psf_gt_group">',
//            '      <input type="text" id="psf_gt_' + ts + '" class="psf_input"',
//            '             placeholder="On Hand greater than" inputmode="decimal"/>',
//            '    </div>',
//
//            '  </div>',
//            '  <div class="psf_actions">',
//            '    <button id="psf_apply_' + ts + '" class="psf_btn psf_btn_apply" type="button">Apply</button>',
//            '    <button id="psf_clear_' + ts + '" class="psf_btn psf_btn_clear" type="button">Clear</button>',
//            '  </div>',
//            '</div>'
//        ].join('');
//
//        listTable.parentElement.insertBefore(bar, listTable);
//        this._psfElement = bar;
//
//        var get = function(id) { return document.getElementById(id); };
//
//        var productInput = get("psf_product_" + ts);
//        var acBox        = get("psf_ac_" + ts);
//        var stockSelect  = get("psf_stock_" + ts);
//        var gtInput      = get("psf_gt_" + ts);
//        var applyBtn     = get("psf_apply_" + ts);
//        var clearBtn     = get("psf_clear_" + ts);
//
//        // Numeric-only validation for gt input
//        gtInput.addEventListener("input", function() {
//            if (!/^-?\d*\.?\d*$/.test(this.value)) {
//                this.value = this.value.slice(0, -1);
//            }
//        });
//
//        var self = this;
//
//        // Apply domain
//        var doApply = function() {
//            var domain = [];
//
//            var pid = parseInt(productInput.getAttribute("data-product-id") || "0");
//            var ptxt = productInput.value.trim();
//            if (pid) {
//                domain.push(["id", "=", pid]);
//            } else if (ptxt) {
//                domain.push("|");
//                domain.push(["name", "ilike", ptxt]);
//                domain.push(["default_code", "ilike", ptxt]);
//            }
//
//            var sv = stockSelect.value;
//            if (sv === "zero")     domain.push(["qty_available", "=", 0]);
//            if (sv === "negative") domain.push(["qty_available", "<", 0]);
//            if (sv === "positive") domain.push(["qty_available", ">", 0]);
//
//            var gt = parseFloat(gtInput.value);
//            if (gtInput.value.trim() && !isNaN(gt)) {
//                domain.push(["qty_available", ">", gt]);
//            }
//
//            if (self.model && self.model.load) {
//                self.model.load({ domain: domain }).catch(function(err) {
//                    console.warn("PSF apply error:", err);
//                });
//                self.notification.add("Filters applied", { type: "success" });
//            }
//        };
//
//        // Clear
//        var doClear = function() {
//            productInput.value = "";
//            productInput.removeAttribute("data-product-id");
//            acBox.style.display = "none";
//            acBox.innerHTML = "";
//            stockSelect.value = "";
//            gtInput.value = "";
//
//            if (self.model && self.model.load) {
//                self.model.load({ domain: [] }).catch(function(err) {
//                    console.warn("PSF clear error:", err);
//                });
//                self.notification.add("Filters cleared", { type: "info" });
//            }
//        };
//
//        applyBtn.addEventListener("click", doApply);
//        clearBtn.addEventListener("click", doClear);
//
//        // Keyboard shortcuts
//        this._psfKeyHandler = function(e) {
//            if (e.key === "Enter") {
//                var acOpen = acBox.style.display !== "none";
//                var acActive = acBox.querySelector(".psf_ac_item.active");
//                if (acOpen && acActive) return;
//                e.preventDefault();
//                doApply();
//            }
//            if (e.key === "Escape") {
//                if (acBox.style.display !== "none") {
//                    acBox.style.display = "none";
//                } else {
//                    doClear();
//                }
//            }
//        };
//        document.addEventListener("keydown", this._psfKeyHandler);
//
//        // Autocomplete
//        var showAc = function(products) {
//            acBox.innerHTML = "";
//            if (!products.length) { acBox.style.display = "none"; return; }
//            products.forEach(function(p) {
//                var item = document.createElement("div");
//                item.className = "psf_ac_item";
//                item.setAttribute("data-id", p.id);
//                item.setAttribute("data-name", p.display_name);
//                var badge = p.default_code
//                    ? '<span class="psf_ac_badge">' + p.default_code + '</span>'
//                    : '';
//                item.innerHTML = badge + '<span class="psf_ac_name">' + p.display_name + '</span>';
//                item.addEventListener("mousedown", function(ev) {
//                    ev.preventDefault();
//                    productInput.value = p.display_name;
//                    productInput.setAttribute("data-product-id", p.id);
//                    acBox.style.display = "none";
//                });
//                acBox.appendChild(item);
//            });
//            acBox.style.display = "block";
//        };
//
//        productInput.addEventListener("input", function() {
//            productInput.removeAttribute("data-product-id");
//            var q = productInput.value.trim();
//            clearTimeout(self._psfDebounce);
//            if (!q) { acBox.style.display = "none"; acBox.innerHTML = ""; return; }
//            self._psfDebounce = setTimeout(function() {
//                self.orm.searchRead(
//                    "product.template",
//                    ["|", ["name", "ilike", q], ["default_code", "ilike", q]],
//                    ["id", "display_name", "default_code"],
//                    { limit: 10 }
//                ).then(function(results) {
//                    showAc(results);
//                }).catch(function(err) {
//                    console.warn("PSF autocomplete error:", err);
//                });
//            }, 280);
//        });
//
//        productInput.addEventListener("keydown", function(e) {
//            if (acBox.style.display === "none") return;
//            var items = acBox.querySelectorAll(".psf_ac_item");
//            if (!items.length) return;
//            var active = acBox.querySelector(".psf_ac_item.active");
//            var idx = Array.from(items).indexOf(active);
//
//            if (e.key === "ArrowDown") {
//                e.preventDefault();
//                if (active) active.classList.remove("active");
//                idx = (idx + 1) % items.length;
//                items[idx].classList.add("active");
//                items[idx].scrollIntoView({ block: "nearest" });
//            } else if (e.key === "ArrowUp") {
//                e.preventDefault();
//                if (active) active.classList.remove("active");
//                idx = (idx - 1 + items.length) % items.length;
//                items[idx].classList.add("active");
//                items[idx].scrollIntoView({ block: "nearest" });
//            } else if (e.key === "Enter" && active) {
//                e.preventDefault();
//                e.stopPropagation();
//                productInput.value = active.getAttribute("data-name");
//                productInput.setAttribute("data-product-id", active.getAttribute("data-id"));
//                acBox.style.display = "none";
//            } else if (e.key === "Escape") {
//                acBox.style.display = "none";
//            }
//        });
//
//        acBox.addEventListener("mouseleave", function() {
//            acBox.querySelectorAll(".psf_ac_item.active").forEach(function(el) {
//                el.classList.remove("active");
//            });
//        });
//
//        this._psfClickOutside = function(e) {
//            if (!productInput.contains(e.target) && !acBox.contains(e.target)) {
//                acBox.style.display = "none";
//            }
//        };
//        document.addEventListener("mousedown", this._psfClickOutside);
//    },
//});
