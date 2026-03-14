/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {

    setup() {
        super.setup(...arguments);
        this._pizClickHandler = null;
        this._pizMutationObs  = null;

        onMounted(() => {
            if (this.props.resModel === "product.template" ||
                this.props.resModel === "product.product") {
                this._pizInit();
            }
        });

        onWillUnmount(() => {
            this._pizCleanup();
        });
    },

    _pizCleanup() {
        if (this._pizClickHandler) {
            document.removeEventListener("click", this._pizClickHandler, true);
            this._pizClickHandler = null;
        }
        if (this._pizMutationObs) {
            this._pizMutationObs.disconnect();
            this._pizMutationObs = null;
        }
    },

    _pizInit() {
        var self = this;

        function applyZoomCursor() {
            document.querySelectorAll(".o_field_image img").forEach(function(img) {
                img.style.cursor = "zoom-in";
            });
        }
        applyZoomCursor();

        this._pizMutationObs = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length) { applyZoomCursor(); break; }
            }
        });
        this._pizMutationObs.observe(document.body, { childList: true, subtree: true });

        this._pizClickHandler = function(e) {
            var t = e.target;
            if (!t || t.tagName !== "IMG") return;

            var node = t.parentElement;
            var inside = false;
            for (var i = 0; i < 10; i++) {
                if (!node) break;
                if (node.classList && node.classList.contains("o_field_image")) { inside = true; break; }
                node = node.parentElement;
            }
            if (!inside) return;

            var src = t.getAttribute("src") || t.src || "";
            if (!src) return;
            if (src.indexOf("placeholder") !== -1) return;
            if (src.substring(0, 5) === "data:" && src.length < 300) return;

            e.stopPropagation();
            e.preventDefault();

            self._pizOpenLightbox(self._pizFullUrl(t));
        };

        document.addEventListener("click", this._pizClickHandler, true);
    },

    _pizFullUrl(imgEl) {
        var src = (imgEl.getAttribute("src") || imgEl.src || "").split("?")[0];
        var m = src.match(/(\/web\/image\/(?:[^/]+\/)\d+\/)([^/?#]*)/);
        if (m) return m[1] + "image_1920";
        var resId = this.model && this.model.root && this.model.root.resId;
        if (resId) {
            return "/web/image/" + (this.props.resModel || "product.template") + "/" + resId + "/image_1920";
        }
        return src;
    },

    _pizOpenLightbox(src) {
        // ── build DOM ────────────────────────────────────────────────────────
        var root = _pizEl("div", "piz-root");

        var stage = _pizEl("div", "piz-stage");
        root.appendChild(stage);

        var wrap = _pizEl("div", "piz-wrap");
        stage.appendChild(wrap);

        var loader = _pizEl("div", "piz-loader");
        loader.textContent = "Loading…";
        root.appendChild(loader);   // appended to root, not wrap

        var closeBtn = _pizEl("div", "piz-x");
        closeBtn.innerHTML = "&times;";
        root.appendChild(closeBtn);

        var hint = _pizEl("div", "piz-hint");
        hint.textContent = "Scroll to zoom  ·  Drag to pan  ·  Esc to close";
        root.appendChild(hint);

        var bar    = _pizEl("div", "piz-bar");
        var bOut   = _pizBtn("\u2212");
        var label  = _pizEl("div", "piz-pct"); label.textContent = "100%";
        var bIn    = _pizBtn("+");
        var bReset = _pizBtn("\u21BA");
        [bOut, label, bIn, bReset].forEach(function(n) { bar.appendChild(n); });
        root.appendChild(bar);

        // Append to body directly — avoids any Odoo layout offset
        document.body.appendChild(root);
        var savedOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        // ── state ────────────────────────────────────────────────────────────
        var scale = 1, tx = 0, ty = 0;
        var MIN = 0.2, MAX = 8;
        var dragging = false, mx = 0, my = 0;
        var imgW = 0, imgH = 0;  // natural image size after load

        // Centre: shift wrap by -imgW/2, -imgH/2 so image centre is at 50%/50%
        function draw() {
            var ox = -imgW / 2;
            var oy = -imgH / 2;
            wrap.style.transform =
                "translate(" + (ox + tx) + "px, " + (oy + ty) + "px) scale(" + scale + ")";
            label.textContent = Math.round(scale * 100) + "%";
        }

        function zoom(d, ox, oy) {
            var r   = stage.getBoundingClientRect();
            var cx  = (ox !== undefined) ? ox : r.left + r.width  / 2;
            var cy  = (oy !== undefined) ? oy : r.top  + r.height / 2;

            // current image centre in viewport coords
            var icx = r.left + r.width  / 2 + tx;
            var icy = r.top  + r.height / 2 + ty;

            var p   = scale;
            scale   = Math.min(MAX, Math.max(MIN, scale + d));
            var ratio = scale / p;
            tx = cx + ratio * (icx - cx) - (r.left + r.width  / 2);
            ty = cy + ratio * (icy - cy) - (r.top  + r.height / 2);
            draw();
        }

        function reset() { scale = 1; tx = 0; ty = 0; draw(); }

        function destroy() {
            document.removeEventListener("keydown", onKey);
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup",   onMouseUp);
            document.body.style.overflow = savedOverflow;
            root.style.transition = "opacity 0.15s";
            root.style.opacity    = "0";
            setTimeout(function() {
                if (root.parentNode) root.parentNode.removeChild(root);
            }, 160);
        }

        // ── load image ───────────────────────────────────────────────────────
        var img = new window.Image();
        img.draggable = false;
        img.onload = function() {
            if (loader.parentNode) loader.parentNode.removeChild(loader);

            // Compute display size (capped at 80vw / 80vh)
            var maxW = window.innerWidth  * 0.80;
            var maxH = window.innerHeight * 0.80;
            var ratio = Math.min(1, maxW / img.naturalWidth, maxH / img.naturalHeight);
            imgW = img.naturalWidth  * ratio;
            imgH = img.naturalHeight * ratio;
            img.style.width  = imgW + "px";
            img.style.height = imgH + "px";

            wrap.appendChild(img);
            draw();
        };
        img.onerror = function() {
            loader.textContent = "Image could not be loaded.";
            loader.style.color = "#f88";
        };
        img.src = src;

        // ── events ───────────────────────────────────────────────────────────
        stage.addEventListener("click", function(e) {
            if (e.target === stage) destroy();
        });
        closeBtn.addEventListener("click", destroy);

        function onKey(e) {
            if      (e.key === "Escape")             destroy();
            else if (e.key === "+" || e.key === "=") zoom(0.2);
            else if (e.key === "-")                  zoom(-0.2);
            else if (e.key === "0")                  reset();
        }
        document.addEventListener("keydown", onKey);

        stage.addEventListener("wheel", function(e) {
            e.preventDefault();
            zoom(e.deltaY < 0 ? 0.15 : -0.15, e.clientX, e.clientY);
        }, { passive: false });

        stage.addEventListener("mousedown", function(e) {
            if (e.button !== 0) return;
            dragging = true; mx = e.clientX; my = e.clientY;
            stage.style.cursor = "grabbing";
            e.preventDefault();
        });
        function onMouseMove(e) {
            if (!dragging) return;
            tx += e.clientX - mx; ty += e.clientY - my;
            mx = e.clientX; my = e.clientY;
            draw();
        }
        function onMouseUp() { dragging = false; stage.style.cursor = "grab"; }
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup",   onMouseUp);

        // Touch
        var td = null, ttx = null, tty = null;
        stage.addEventListener("touchstart", function(e) {
            if (e.touches.length === 2) {
                var dx = e.touches[0].clientX - e.touches[1].clientX;
                var dy = e.touches[0].clientY - e.touches[1].clientY;
                td = Math.sqrt(dx*dx + dy*dy); ttx = null;
            } else if (e.touches.length === 1) {
                ttx = e.touches[0].clientX; tty = e.touches[0].clientY; td = null;
            }
        }, { passive: true });
        stage.addEventListener("touchmove", function(e) {
            e.preventDefault();
            if (e.touches.length === 2 && td !== null) {
                var dx2 = e.touches[0].clientX - e.touches[1].clientX;
                var dy2 = e.touches[0].clientY - e.touches[1].clientY;
                var d   = Math.sqrt(dx2*dx2 + dy2*dy2);
                scale = Math.min(MAX, Math.max(MIN, scale * (d / td)));
                td = d; draw();
            } else if (e.touches.length === 1 && ttx !== null) {
                tx += e.touches[0].clientX - ttx;
                ty += e.touches[0].clientY - tty;
                ttx = e.touches[0].clientX; tty = e.touches[0].clientY;
                draw();
            }
        }, { passive: false });
        stage.addEventListener("touchend", function() { td = null; ttx = null; tty = null; });

        bIn.addEventListener("click",    function(e) { e.stopPropagation(); zoom(0.25); });
        bOut.addEventListener("click",   function(e) { e.stopPropagation(); zoom(-0.25); });
        bReset.addEventListener("click", function(e) { e.stopPropagation(); reset(); });
    },
});

function _pizEl(tag, cls) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    return n;
}
function _pizBtn(html) {
    var b = _pizEl("div", "piz-btn");
    b.innerHTML = html;
    return b;
}

