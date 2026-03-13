/**
 * product_image_zoom/static/src/js/image_zoom.js
 *
 * Strategy: plain document-level click delegation.
 * No OWL patching — works reliably with Odoo 19 CE.
 *
 * Listens for clicks on <img> elements that live inside
 * .o_field_image (the class Odoo adds to every ImageField widget).
 * Opens a full-screen lightbox with scroll/pinch zoom + drag-to-pan.
 */

(function () {
    "use strict";

    // ── helpers ────────────────────────────────────────────────────────────────

    function clamp(val, min, max) {
        return Math.min(max, Math.max(min, val));
    }

    function touchDist(touches) {
        var dx = touches[0].clientX - touches[1].clientX;
        var dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // ── Lightbox ───────────────────────────────────────────────────────────────

    function Lightbox(src) {
        this.src = src;
        this.scale = 1;
        this.tx = 0;   // translate X (px, relative to natural centre)
        this.ty = 0;   // translate Y
        this.MIN = 0.3;
        this.MAX = 6;

        // drag state
        this._drag = false;
        this._lastX = 0;
        this._lastY = 0;

        // touch pinch state
        this._lastDist = null;
        this._lastTX = null;
        this._lastTY = null;

        this._build();
        this._bind();
        document.body.appendChild(this.overlay);
        // prevent body scroll while open
        this._bodyOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
    }

    Lightbox.prototype._build = function () {
        /* overlay */
        this.overlay = el("div", "piz-overlay");

        /* full-area stage (click backdrop → close) */
        this.stage = el("div", "piz-stage");
        this.overlay.appendChild(this.stage);

        /* image wrapper — centred by CSS top:50% left:50%, JS adds tx/ty/scale */
        this.wrap = el("div", "piz-img-wrap");
        this.img = document.createElement("img");
        this.img.src = this.src;
        this.wrap.appendChild(this.img);
        this.stage.appendChild(this.wrap);

        /* close button */
        this.closeBtn = el("div", "piz-close");
        this.closeBtn.innerHTML = "&times;";
        this.overlay.appendChild(this.closeBtn);

        /* hint */
        var hint = el("div", "piz-hint");
        hint.textContent = "Scroll to zoom · Drag to pan · Esc to close";
        this.overlay.appendChild(hint);

        /* controls */
        this.controls = el("div", "piz-controls");
        this.btnOut  = mkBtn("&minus;");
        this.pct     = el("div", "piz-pct"); this.pct.textContent = "100%";
        this.btnIn   = mkBtn("&plus;");
        this.btnReset = mkBtn("&#8635;");
        this.btnReset.title = "Reset (0)";
        [this.btnOut, this.pct, this.btnIn, this.btnReset].forEach(function (n) {
            this.controls.appendChild(n);
        }, this);
        this.overlay.appendChild(this.controls);

        this._applyTransform();
    };

    Lightbox.prototype._bind = function () {
        var self = this;

        /* close on backdrop / close button */
        this.stage.addEventListener("click", function (e) {
            if (e.target === self.stage) self.destroy();
        });
        this.closeBtn.addEventListener("click", function () { self.destroy(); });

        /* keyboard */
        this._onKey = function (e) {
            if (e.key === "Escape")        { self.destroy(); }
            else if (e.key === "+"  || e.key === "=") { self._zoom(0.2); }
            else if (e.key === "-")        { self._zoom(-0.2); }
            else if (e.key === "0")        { self._reset(); }
        };
        document.addEventListener("keydown", this._onKey);

        /* scroll-wheel zoom */
        this.stage.addEventListener("wheel", function (e) {
            e.preventDefault();
            var delta = e.deltaY < 0 ? 0.15 : -0.15;
            self._zoom(delta, e.clientX, e.clientY);
        }, { passive: false });

        /* mouse drag */
        this.stage.addEventListener("mousedown", function (e) {
            if (e.button !== 0) return;
            self._drag = true;
            self._lastX = e.clientX;
            self._lastY = e.clientY;
            self.stage.classList.add("dragging");
            e.preventDefault();
        });
        document.addEventListener("mousemove", function (e) {
            if (!self._drag) return;
            self.tx += e.clientX - self._lastX;
            self.ty += e.clientY - self._lastY;
            self._lastX = e.clientX;
            self._lastY = e.clientY;
            self._applyTransform();
        });
        document.addEventListener("mouseup", function () {
            self._drag = false;
            self.stage.classList.remove("dragging");
        });

        /* touch pinch + pan */
        this.stage.addEventListener("touchstart", function (e) {
            if (e.touches.length === 2) {
                self._lastDist = touchDist(e.touches);
                self._lastTX = null; self._lastTY = null;
            } else if (e.touches.length === 1) {
                self._lastTX = e.touches[0].clientX;
                self._lastTY = e.touches[0].clientY;
                self._lastDist = null;
            }
        }, { passive: true });

        this.stage.addEventListener("touchmove", function (e) {
            e.preventDefault();
            if (e.touches.length === 2 && self._lastDist) {
                var d = touchDist(e.touches);
                var ratio = d / self._lastDist;
                self.scale = clamp(self.scale * ratio, self.MIN, self.MAX);
                self._lastDist = d;
                self._applyTransform();
            } else if (e.touches.length === 1 && self._lastTX !== null) {
                self.tx += e.touches[0].clientX - self._lastTX;
                self.ty += e.touches[0].clientY - self._lastTY;
                self._lastTX = e.touches[0].clientX;
                self._lastTY = e.touches[0].clientY;
                self._applyTransform();
            }
        }, { passive: false });

        this.stage.addEventListener("touchend", function () {
            self._lastDist = null; self._lastTX = null; self._lastTY = null;
        });

        /* control buttons */
        this.btnIn.addEventListener("click",    function (e) { e.stopPropagation(); self._zoom(0.25); });
        this.btnOut.addEventListener("click",   function (e) { e.stopPropagation(); self._zoom(-0.25); });
        this.btnReset.addEventListener("click", function (e) { e.stopPropagation(); self._reset(); });
    };

    /**
     * Zoom by `delta` scale units, optionally anchored to a viewport point (ox, oy).
     * If no anchor given, zoom around centre of stage.
     */
    Lightbox.prototype._zoom = function (delta, ox, oy) {
        var rect   = this.stage.getBoundingClientRect();
        var cx     = (ox !== undefined) ? ox : rect.left + rect.width  / 2;
        var cy     = (oy !== undefined) ? oy : rect.top  + rect.height / 2;

        // image centre in viewport coords
        var imgCX  = rect.left + rect.width  / 2 + this.tx;
        var imgCY  = rect.top  + rect.height / 2 + this.ty;

        var prev   = this.scale;
        this.scale = clamp(this.scale + delta, this.MIN, this.MAX);
        var ratio  = this.scale / prev;

        // keep the point under cursor fixed
        this.tx    = cx + ratio * (imgCX - cx) - (rect.left + rect.width  / 2);
        this.ty    = cy + ratio * (imgCY - cy) - (rect.top  + rect.height / 2);

        this._applyTransform();
    };

    Lightbox.prototype._reset = function () {
        this.scale = 1; this.tx = 0; this.ty = 0;
        this._applyTransform();
    };

    Lightbox.prototype._applyTransform = function () {
        // The img has translate(-50%,-50%) from CSS to centre it at top:50% left:50%
        // We add tx/ty for drag offset and scale around that centre.
        this.wrap.style.transform =
            "translate(calc(-50% + " + this.tx + "px), calc(-50% + " + this.ty + "px)) scale(" + this.scale + ")";
        if (this.pct) {
            this.pct.textContent = Math.round(this.scale * 100) + "%";
        }
    };

    Lightbox.prototype.destroy = function () {
        var self = this;
        document.removeEventListener("keydown", this._onKey);
        document.body.style.overflow = this._bodyOverflow;
        this.overlay.classList.add("piz-closing");
        setTimeout(function () {
            if (self.overlay.parentNode) {
                self.overlay.parentNode.removeChild(self.overlay);
            }
        }, 160);
    };

    // ── DOM helpers ────────────────────────────────────────────────────────────

    function el(tag, cls) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        return node;
    }
    function mkBtn(html) {
        var b = el("div", "piz-btn");
        b.innerHTML = html;
        return b;
    }

    // ── Global click delegation ────────────────────────────────────────────────
    //
    // We listen at document level (capture phase so we run before Odoo handlers).
    // We open the lightbox only when:
    //   1. The clicked element is an <img>
    //   2. It lives inside a .o_field_image wrapper (Odoo's ImageField)
    //   3. It has a real src (not a placeholder / empty blob)
    //
    // Using capture=true means we also intercept clicks that Odoo might otherwise
    // swallow with stopPropagation on the bubble phase.

    function isProductImage(imgEl) {
        // Walk up max 8 levels looking for the Odoo field wrapper
        var node = imgEl.parentElement;
        for (var i = 0; i < 8; i++) {
            if (!node) break;
            if (node.classList && node.classList.contains("o_field_image")) {
                return true;
            }
            node = node.parentElement;
        }
        return false;
    }

    function isPlaceholder(src) {
        if (!src) return true;
        // Odoo placeholder: ends with /web/static/img/placeholder.png  or is a tiny data URI
        if (src.indexOf("placeholder") !== -1) return true;
        // very small data URI (blank / icon placeholder)
        if (src.startsWith("data:") && src.length < 200) return true;
        return false;
    }

    document.addEventListener("click", function (e) {
        var target = e.target;
        if (!target || target.tagName !== "IMG") return;
        if (!isProductImage(target)) return;

        var src = target.src || target.getAttribute("src");
        if (isPlaceholder(src)) return;

        // Prevent Odoo's own click handlers from also firing (e.g. file-picker)
        e.stopPropagation();
        e.preventDefault();

        new Lightbox(src);
    }, true /* capture */);

    // Also make the cursor look right as soon as the page loads / navigates
    // (MutationObserver keeps it applied after OWL re-renders)
    function applyCursor() {
        var imgs = document.querySelectorAll(".o_field_image img");
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].style.cursor = "zoom-in";
        }
    }

    var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
            var added = mutations[i].addedNodes;
            for (var j = 0; j < added.length; j++) {
                if (added[j].nodeType === 1) { // ELEMENT_NODE
                    applyCursor();
                    break;
                }
            }
        }
    });

    // Start observing once the DOM is ready
    function init() {
        applyCursor();
        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
