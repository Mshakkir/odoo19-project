/**
 * product_image_zoom/static/src/js/image_zoom.js
 * Odoo 19 CE — plain IIFE, no OWL patching required.
 *
 * KEY FIX: uses /web/image/<model>/<id>/image_1920 to load the
 *          original full-resolution image instead of the thumbnail.
 */

(function () {
    "use strict";

    function clamp(v, mn, mx) { return Math.min(mx, Math.max(mn, v)); }

    function touchDist(t) {
        var dx = t[0].clientX - t[1].clientX, dy = t[0].clientY - t[1].clientY;
        return Math.sqrt(dx*dx + dy*dy);
    }

    // ── Full-resolution URL ────────────────────────────────────────────────────
    // Odoo renders the ImageField as a small thumbnail (often image_128 or a
    // resized blob). We rebuild the URL pointing to image_1920 so the lightbox
    // shows the stored original image.

    function getFullResUrl(imgEl) {
        var src = (imgEl.getAttribute("src") || imgEl.src || "").split("?")[0];

        // Case 1: already a /web/image/... URL → swap the field name
        // e.g. /web/image/product.template/42/image_128
        //   or /web/image/42/image_128
        var m = src.match(/^(\/web\/image\/[^/]+\/\d+\/)([^/?#]+)/);
        if (m) {
            return m[1] + "image_1920";
        }

        // Case 2: data: URI or /web/image/... without field segment
        // → try to build URL from record id in the page URL
        var id = null;

        // Odoo 17+ URL style: /odoo/inventory/products/123
        var pathM = window.location.pathname.match(/\/(\d+)(?:\/|$)/);
        if (pathM) id = pathM[1];

        // Also check hash/query ?id=123
        if (!id) {
            var hM = window.location.href.match(/[?&#]id=(\d+)/);
            if (hM) id = hM[1];
        }

        // Determine model (default product.template for inventory products)
        var model = "product.template";
        if (window.location.href.indexOf("product.product") !== -1) {
            model = "product.product";
        }

        if (id) {
            return "/web/image/" + model + "/" + id + "/image_1920";
        }

        // Fallback: strip size params and hope for the best
        return src;
    }

    // ── Lightbox ───────────────────────────────────────────────────────────────

    function Lightbox(src) {
        this.scale = 1;
        this.tx = 0; this.ty = 0;
        this.MIN = 0.3; this.MAX = 6;
        this._drag = false;
        this._lastX = 0; this._lastY = 0;
        this._lastDist = null; this._lastTX = null; this._lastTY = null;
        this._build(src);
        this._bind();
        document.body.appendChild(this.overlay);
        this._prevOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
    }

    Lightbox.prototype._build = function (src) {
        this.overlay = mk("div", "piz-overlay");

        this.stage = mk("div", "piz-stage");
        this.overlay.appendChild(this.stage);

        this.wrap = mk("div", "piz-img-wrap");
        // Loading spinner text
        this.wrap.innerHTML = '<div class="piz-loading">Loading…</div>';

        this.img = new Image();
        var self = this;
        this.img.onload = function () {
            self.wrap.innerHTML = "";
            self.wrap.appendChild(self.img);
            self._applyTransform();
        };
        this.img.onerror = function () {
            // Full-res failed → fall back to thumbnail src passed in
            self.wrap.innerHTML = '<div class="piz-loading" style="color:#f66">Image load failed</div>';
        };
        this.img.src = src;
        this.img.draggable = false;

        this.stage.appendChild(this.wrap);

        // Close
        this.closeBtn = mk("div", "piz-close");
        this.closeBtn.innerHTML = "&times;";
        this.overlay.appendChild(this.closeBtn);

        // Hint
        var hint = mk("div", "piz-hint");
        hint.textContent = "Scroll to zoom  ·  Drag to pan  ·  Esc to close";
        this.overlay.appendChild(hint);

        // Controls
        this.controls = mk("div", "piz-controls");
        this.btnOut   = mkBtn("&minus;");
        this.pct      = mk("div", "piz-pct"); this.pct.textContent = "100%";
        this.btnIn    = mkBtn("&plus;");
        this.btnReset = mkBtn("&#8635;");
        [this.btnOut, this.pct, this.btnIn, this.btnReset].forEach(function (n) {
            self.controls.appendChild(n);
        });
        this.overlay.appendChild(this.controls);

        this._applyTransform();
    };

    Lightbox.prototype._bind = function () {
        var self = this;

        this.stage.addEventListener("click", function (e) {
            if (e.target === self.stage) self.destroy();
        });
        this.closeBtn.addEventListener("click", function () { self.destroy(); });

        this._onKey = function (e) {
            if (e.key === "Escape") self.destroy();
            else if (e.key === "+" || e.key === "=") self._zoom(0.2);
            else if (e.key === "-") self._zoom(-0.2);
            else if (e.key === "0") self._reset();
        };
        document.addEventListener("keydown", this._onKey);

        this.stage.addEventListener("wheel", function (e) {
            e.preventDefault();
            self._zoom(e.deltaY < 0 ? 0.15 : -0.15, e.clientX, e.clientY);
        }, { passive: false });

        this.stage.addEventListener("mousedown", function (e) {
            if (e.button !== 0) return;
            self._drag = true;
            self._lastX = e.clientX; self._lastY = e.clientY;
            self.stage.classList.add("dragging");
            e.preventDefault();
        });
        document.addEventListener("mousemove", function (e) {
            if (!self._drag) return;
            self.tx += e.clientX - self._lastX;
            self.ty += e.clientY - self._lastY;
            self._lastX = e.clientX; self._lastY = e.clientY;
            self._applyTransform();
        });
        document.addEventListener("mouseup", function () {
            self._drag = false;
            self.stage.classList.remove("dragging");
        });

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
                self.scale = clamp(self.scale * (d / self._lastDist), self.MIN, self.MAX);
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

        this.btnIn.addEventListener("click",    function (e) { e.stopPropagation(); self._zoom(0.25); });
        this.btnOut.addEventListener("click",   function (e) { e.stopPropagation(); self._zoom(-0.25); });
        this.btnReset.addEventListener("click", function (e) { e.stopPropagation(); self._reset(); });
    };

    Lightbox.prototype._zoom = function (delta, ox, oy) {
        var rect = this.stage.getBoundingClientRect();
        var cx = (ox !== undefined) ? ox : rect.left + rect.width  / 2;
        var cy = (oy !== undefined) ? oy : rect.top  + rect.height / 2;
        var imgCX = rect.left + rect.width  / 2 + this.tx;
        var imgCY = rect.top  + rect.height / 2 + this.ty;
        var prev  = this.scale;
        this.scale = clamp(this.scale + delta, this.MIN, this.MAX);
        var ratio = this.scale / prev;
        this.tx = cx + ratio * (imgCX - cx) - (rect.left + rect.width  / 2);
        this.ty = cy + ratio * (imgCY - cy) - (rect.top  + rect.height / 2);
        this._applyTransform();
    };

    Lightbox.prototype._reset = function () {
        this.scale = 1; this.tx = 0; this.ty = 0;
        this._applyTransform();
    };

    Lightbox.prototype._applyTransform = function () {
        this.wrap.style.transform =
            "translate(calc(-50% + " + this.tx + "px), calc(-50% + " + this.ty + "px)) scale(" + this.scale + ")";
        if (this.pct) this.pct.textContent = Math.round(this.scale * 100) + "%";
    };

    Lightbox.prototype.destroy = function () {
        var self = this;
        document.removeEventListener("keydown", this._onKey);
        document.body.style.overflow = this._prevOverflow;
        this.overlay.classList.add("piz-closing");
        setTimeout(function () {
            if (self.overlay.parentNode) self.overlay.parentNode.removeChild(self.overlay);
        }, 160);
    };

    // ── DOM helpers ────────────────────────────────────────────────────────────

    function mk(tag, cls) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        return n;
    }
    function mkBtn(html) {
        var b = mk("div", "piz-btn"); b.innerHTML = html; return b;
    }

    // ── Click delegation ───────────────────────────────────────────────────────

    function isInsideImageField(imgEl) {
        var n = imgEl.parentElement;
        for (var i = 0; i < 8; i++) {
            if (!n) break;
            if (n.classList && n.classList.contains("o_field_image")) return true;
            n = n.parentElement;
        }
        return false;
    }

    function isPlaceholder(src) {
        if (!src) return true;
        if (src.indexOf("placeholder") !== -1) return true;
        if (src.startsWith("data:") && src.length < 200) return true;
        return false;
    }

    document.addEventListener("click", function (e) {
        var t = e.target;
        if (!t || t.tagName !== "IMG") return;
        if (!isInsideImageField(t)) return;
        var thumb = t.src || t.getAttribute("src") || "";
        if (isPlaceholder(thumb)) return;

        e.stopPropagation();
        e.preventDefault();

        new Lightbox(getFullResUrl(t));
    }, true);

    // ── Cursor styling via MutationObserver ────────────────────────────────────

    function applyCursor() {
        document.querySelectorAll(".o_field_image img").forEach(function (img) {
            img.style.cursor = "zoom-in";
        });
    }

    new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
            if (muts[i].addedNodes.length) { applyCursor(); break; }
        }
    }).observe(document.body, { childList: true, subtree: true });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", applyCursor);
    } else {
        applyCursor();
    }

})();
