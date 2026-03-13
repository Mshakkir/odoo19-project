/** @odoo-module **/
/**
 * Product Image Zoom - Odoo 19 CE
 * Opens full-resolution image_1920 in a lightbox when the product image is clicked.
 */

(function () {
    "use strict";

    /* ── tiny helpers ─────────────────────────────────────────────────────── */
    function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }

    function el(tag, cls) {
        var n = document.createElement(tag);
        if (cls) { n.className = cls; }
        return n;
    }

    function btn(html) {
        var b = el("div", "piz-btn");
        b.innerHTML = html;
        return b;
    }

    /* ── build full-res URL ───────────────────────────────────────────────── */
    function fullResUrl(imgEl) {
        var src = imgEl.getAttribute("src") || imgEl.src || "";

        // Strip query string for matching
        var base = src.split("?")[0];

        // Pattern: /web/image/MODEL/ID/FIELD  or  /web/image/ID/FIELD
        var m = base.match(/(\/web\/image\/(?:[^/]+\/)\d+\/)([^/?#]*)/);
        if (m) {
            return m[1] + "image_1920";
        }

        // Try to get record id from page URL path  e.g. /odoo/.../products/42
        var pid = null;
        var pm = window.location.pathname.match(/\/(\d+)(?:\/|$)/);
        if (pm) { pid = pm[1]; }

        if (!pid) {
            var hm = window.location.search.match(/[?&]id=(\d+)/);
            if (hm) { pid = hm[1]; }
        }

        if (pid) {
            return "/web/image/product.template/" + pid + "/image_1920";
        }

        // Last resort: return original src
        return src;
    }

    /* ── Lightbox ─────────────────────────────────────────────────────────── */
    function Lightbox(src) {
        this.scale  = 1;
        this.tx     = 0;
        this.ty     = 0;
        this.MIN    = 0.2;
        this.MAX    = 8;
        this._dragging = false;
        this._mx    = 0;
        this._my    = 0;
        this._td    = null;
        this._ttx   = null;
        this._tty   = null;
        this._src   = src;

        this._render();
        this._listen();
        document.body.appendChild(this.root);
        this._savedOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
    }

    Lightbox.prototype._render = function () {
        var self = this;

        // backdrop
        this.root = el("div", "piz-root");

        // stage (click outside → close)
        this.stage = el("div", "piz-stage");
        this.root.appendChild(this.stage);

        // image wrapper
        this.wrap = el("div", "piz-wrap");
        this.stage.appendChild(this.wrap);

        // loading text
        this.loader = el("div", "piz-loader");
        this.loader.textContent = "Loading…";
        this.wrap.appendChild(this.loader);

        // image
        this.image = new window.Image();
        this.image.draggable = false;
        this.image.onload = function () {
            if (self.loader && self.loader.parentNode) {
                self.loader.parentNode.removeChild(self.loader);
            }
            self.wrap.appendChild(self.image);
            self._draw();
        };
        this.image.onerror = function () {
            self.loader.textContent = "Could not load image.";
            self.loader.style.color = "#f88";
        };
        this.image.src = this._src;

        // close button
        this.closeBtn = el("div", "piz-x");
        this.closeBtn.innerHTML = "&times;";
        this.root.appendChild(this.closeBtn);

        // hint
        var hint = el("div", "piz-hint");
        hint.textContent = "Scroll to zoom  ·  Drag to pan  ·  Esc to close";
        this.root.appendChild(hint);

        // control bar
        var bar     = el("div", "piz-bar");
        this.bOut   = btn("\u2212");
        this.label  = el("div", "piz-pct"); this.label.textContent = "100%";
        this.bIn    = btn("+");
        this.bReset = btn("\u21BA");
        bar.appendChild(this.bOut);
        bar.appendChild(this.label);
        bar.appendChild(this.bIn);
        bar.appendChild(this.bReset);
        this.root.appendChild(bar);

        this._draw();
    };

    Lightbox.prototype._draw = function () {
        var t = "translate(calc(-50% + " + this.tx + "px), calc(-50% + " + this.ty + "px)) scale(" + this.scale + ")";
        this.wrap.style.transform = t;
        this.label.textContent = Math.round(this.scale * 100) + "%";
    };

    Lightbox.prototype._zoom = function (d, ox, oy) {
        var r   = this.stage.getBoundingClientRect();
        var cx  = (ox !== undefined) ? ox : r.left + r.width  / 2;
        var cy  = (oy !== undefined) ? oy : r.top  + r.height / 2;
        var icx = r.left + r.width  / 2 + this.tx;
        var icy = r.top  + r.height / 2 + this.ty;
        var p   = this.scale;
        this.scale = clamp(this.scale + d, this.MIN, this.MAX);
        var ratio = this.scale / p;
        this.tx = cx + ratio * (icx - cx) - (r.left + r.width  / 2);
        this.ty = cy + ratio * (icy - cy) - (r.top  + r.height / 2);
        this._draw();
    };

    Lightbox.prototype._reset = function () {
        this.scale = 1; this.tx = 0; this.ty = 0;
        this._draw();
    };

    Lightbox.prototype.close = function () {
        var self = this;
        document.removeEventListener("keydown", this._kh);
        document.removeEventListener("mousemove", this._mmh);
        document.removeEventListener("mouseup", this._muh);
        document.body.style.overflow = this._savedOverflow;
        this.root.style.opacity = "0";
        this.root.style.transition = "opacity 0.15s";
        setTimeout(function () {
            if (self.root.parentNode) {
                self.root.parentNode.removeChild(self.root);
            }
        }, 160);
    };

    Lightbox.prototype._listen = function () {
        var self = this;

        // backdrop click
        this.stage.addEventListener("click", function (e) {
            if (e.target === self.stage) { self.close(); }
        });
        this.closeBtn.addEventListener("click", function () { self.close(); });

        // keyboard
        this._kh = function (e) {
            if      (e.key === "Escape")             { self.close(); }
            else if (e.key === "+" || e.key === "=") { self._zoom(0.2); }
            else if (e.key === "-")                  { self._zoom(-0.2); }
            else if (e.key === "0")                  { self._reset(); }
        };
        document.addEventListener("keydown", this._kh);

        // scroll zoom
        this.stage.addEventListener("wheel", function (e) {
            e.preventDefault();
            self._zoom(e.deltaY < 0 ? 0.15 : -0.15, e.clientX, e.clientY);
        }, { passive: false });

        // mouse drag
        this.stage.addEventListener("mousedown", function (e) {
            if (e.button !== 0) { return; }
            self._dragging = true;
            self._mx = e.clientX;
            self._my = e.clientY;
            self.stage.style.cursor = "grabbing";
            e.preventDefault();
        });
        this._mmh = function (e) {
            if (!self._dragging) { return; }
            self.tx += e.clientX - self._mx;
            self.ty += e.clientY - self._my;
            self._mx = e.clientX;
            self._my = e.clientY;
            self._draw();
        };
        this._muh = function () {
            self._dragging = false;
            self.stage.style.cursor = "grab";
        };
        document.addEventListener("mousemove", this._mmh);
        document.addEventListener("mouseup",   this._muh);

        // touch
        this.stage.addEventListener("touchstart", function (e) {
            if (e.touches.length === 2) {
                var dx = e.touches[0].clientX - e.touches[1].clientX;
                var dy = e.touches[0].clientY - e.touches[1].clientY;
                self._td = Math.sqrt(dx*dx + dy*dy);
                self._ttx = null;
            } else if (e.touches.length === 1) {
                self._ttx = e.touches[0].clientX;
                self._tty = e.touches[0].clientY;
                self._td  = null;
            }
        }, { passive: true });

        this.stage.addEventListener("touchmove", function (e) {
            e.preventDefault();
            if (e.touches.length === 2 && self._td !== null) {
                var dx2 = e.touches[0].clientX - e.touches[1].clientX;
                var dy2 = e.touches[0].clientY - e.touches[1].clientY;
                var d   = Math.sqrt(dx2*dx2 + dy2*dy2);
                self.scale = clamp(self.scale * (d / self._td), self.MIN, self.MAX);
                self._td = d;
                self._draw();
            } else if (e.touches.length === 1 && self._ttx !== null) {
                self.tx += e.touches[0].clientX - self._ttx;
                self.ty += e.touches[0].clientY - self._tty;
                self._ttx = e.touches[0].clientX;
                self._tty = e.touches[0].clientY;
                self._draw();
            }
        }, { passive: false });

        this.stage.addEventListener("touchend", function () {
            self._td = null; self._ttx = null; self._tty = null;
        });

        // control buttons
        this.bIn.addEventListener("click",    function (e) { e.stopPropagation(); self._zoom(0.25); });
        this.bOut.addEventListener("click",   function (e) { e.stopPropagation(); self._zoom(-0.25); });
        this.bReset.addEventListener("click", function (e) { e.stopPropagation(); self._reset(); });
    };

    /* ── click delegation ─────────────────────────────────────────────────── */

    function insideImageField(img) {
        var n = img.parentElement;
        for (var i = 0; i < 10; i++) {
            if (!n) { return false; }
            if (n.classList && n.classList.contains("o_field_image")) { return true; }
            n = n.parentElement;
        }
        return false;
    }

    function isPlaceholder(src) {
        if (!src) { return true; }
        if (src.indexOf("placeholder") !== -1) { return true; }
        if (src.substring(0, 5) === "data:" && src.length < 300) { return true; }
        return false;
    }

    document.addEventListener("click", function (e) {
        var t = e.target;
        if (!t || t.tagName !== "IMG") { return; }
        if (!insideImageField(t))      { return; }
        var src = t.getAttribute("src") || t.src || "";
        if (isPlaceholder(src))        { return; }
        e.stopPropagation();
        e.preventDefault();
        new Lightbox(fullResUrl(t));
    }, true);

    /* ── cursor ───────────────────────────────────────────────────────────── */

    function setCursor() {
        var imgs = document.querySelectorAll(".o_field_image img");
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].style.cursor = "zoom-in";
        }
    }

    new MutationObserver(function (ms) {
        for (var i = 0; i < ms.length; i++) {
            if (ms[i].addedNodes.length) { setCursor(); break; }
        }
    }).observe(document.body, { childList: true, subtree: true });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setCursor);
    } else {
        setCursor();
    }

}());
