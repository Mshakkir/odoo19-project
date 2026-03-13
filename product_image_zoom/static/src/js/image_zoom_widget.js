/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ImageField } from "@web/views/fields/image/image_field";
import { useEffect, useRef } from "@odoo/owl";

// ─── Lightbox class ──────────────────────────────────────────────────────────

class ImageZoomLightbox {
    constructor(src) {
        this.src = src;
        this.scale = 1;
        this.minScale = 0.5;
        this.maxScale = 5;
        this.translateX = 0;
        this.translateY = 0;
        this.isDragging = false;
        this.lastX = 0;
        this.lastY = 0;

        this._build();
        this._bindEvents();
        document.body.appendChild(this.overlay);
    }

    _build() {
        this.overlay = document.createElement("div");
        this.overlay.className = "piz-overlay";

        this.container = document.createElement("div");
        this.container.className = "piz-container";

        this.wrapper = document.createElement("div");
        this.wrapper.className = "piz-image-wrapper";

        this.img = document.createElement("img");
        this.img.src = this.src;
        this.img.draggable = false;

        this.wrapper.appendChild(this.img);
        this.container.appendChild(this.wrapper);

        // Close button
        this.closeBtn = document.createElement("div");
        this.closeBtn.className = "piz-close";
        this.closeBtn.innerHTML = "&times;";

        // Hint
        this.hint = document.createElement("div");
        this.hint.className = "piz-hint";
        this.hint.textContent = "Scroll to zoom · Drag to pan · Click outside to close";

        // Controls
        this.controls = document.createElement("div");
        this.controls.className = "piz-controls";

        this.zoomOutBtn = document.createElement("div");
        this.zoomOutBtn.className = "piz-btn";
        this.zoomOutBtn.textContent = "−";

        this.zoomLabel = document.createElement("div");
        this.zoomLabel.className = "piz-zoom-label";
        this.zoomLabel.textContent = "100%";

        this.zoomInBtn = document.createElement("div");
        this.zoomInBtn.className = "piz-btn";
        this.zoomInBtn.textContent = "+";

        this.resetBtn = document.createElement("div");
        this.resetBtn.className = "piz-btn";
        this.resetBtn.title = "Reset";
        this.resetBtn.innerHTML = "&#8635;";

        this.controls.appendChild(this.zoomOutBtn);
        this.controls.appendChild(this.zoomLabel);
        this.controls.appendChild(this.zoomInBtn);
        this.controls.appendChild(this.resetBtn);

        this.overlay.appendChild(this.container);
        this.overlay.appendChild(this.closeBtn);
        this.overlay.appendChild(this.hint);
        this.overlay.appendChild(this.controls);
    }

    _bindEvents() {
        // Close on overlay click (not on image/controls)
        this.overlay.addEventListener("click", (e) => {
            if (e.target === this.overlay || e.target === this.container) {
                this.destroy();
            }
        });
        this.closeBtn.addEventListener("click", () => this.destroy());

        // Keyboard
        this._keyHandler = (e) => {
            if (e.key === "Escape") this.destroy();
            if (e.key === "+" || e.key === "=") this._zoom(0.2);
            if (e.key === "-") this._zoom(-0.2);
            if (e.key === "0") this._reset();
        };
        document.addEventListener("keydown", this._keyHandler);

        // Scroll wheel zoom
        this.container.addEventListener("wheel", (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.15 : 0.15;
            this._zoom(delta, e.clientX, e.clientY);
        }, { passive: false });

        // Mouse drag
        this.wrapper.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return;
            this.isDragging = true;
            this.lastX = e.clientX;
            this.lastY = e.clientY;
            this.wrapper.classList.add("piz-dragging");
            e.preventDefault();
        });
        document.addEventListener("mousemove", (e) => {
            if (!this.isDragging) return;
            this.translateX += e.clientX - this.lastX;
            this.translateY += e.clientY - this.lastY;
            this.lastX = e.clientX;
            this.lastY = e.clientY;
            this._applyTransform();
        });
        document.addEventListener("mouseup", () => {
            this.isDragging = false;
            this.wrapper.classList.remove("piz-dragging");
        });

        // Touch pinch zoom + pan
        let lastDist = null;
        let lastTouchX = null;
        let lastTouchY = null;

        this.container.addEventListener("touchstart", (e) => {
            if (e.touches.length === 2) {
                lastDist = this._touchDist(e.touches);
            } else if (e.touches.length === 1) {
                lastTouchX = e.touches[0].clientX;
                lastTouchY = e.touches[0].clientY;
            }
        }, { passive: true });

        this.container.addEventListener("touchmove", (e) => {
            e.preventDefault();
            if (e.touches.length === 2) {
                const dist = this._touchDist(e.touches);
                if (lastDist) {
                    const ratio = dist / lastDist;
                    this.scale = Math.min(this.maxScale, Math.max(this.minScale, this.scale * ratio));
                    this._applyTransform();
                }
                lastDist = dist;
            } else if (e.touches.length === 1 && lastTouchX !== null) {
                this.translateX += e.touches[0].clientX - lastTouchX;
                this.translateY += e.touches[0].clientY - lastTouchY;
                lastTouchX = e.touches[0].clientX;
                lastTouchY = e.touches[0].clientY;
                this._applyTransform();
            }
        }, { passive: false });

        this.container.addEventListener("touchend", () => {
            lastDist = null;
            lastTouchX = null;
            lastTouchY = null;
        });

        // Control buttons
        this.zoomInBtn.addEventListener("click", (e) => { e.stopPropagation(); this._zoom(0.25); });
        this.zoomOutBtn.addEventListener("click", (e) => { e.stopPropagation(); this._zoom(-0.25); });
        this.resetBtn.addEventListener("click", (e) => { e.stopPropagation(); this._reset(); });
    }

    _touchDist(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    _zoom(delta, originX, originY) {
        const rect = this.wrapper.getBoundingClientRect();
        const cx = originX !== undefined ? originX : rect.left + rect.width / 2;
        const cy = originY !== undefined ? originY : rect.top + rect.height / 2;

        const prevScale = this.scale;
        this.scale = Math.min(this.maxScale, Math.max(this.minScale, this.scale + delta));
        const scaleDiff = this.scale / prevScale;

        // Adjust translation so zoom is centred on cursor/pinch point
        this.translateX = cx - scaleDiff * (cx - this.translateX);
        this.translateY = cy - scaleDiff * (cy - this.translateY);

        this._applyTransform();
    }

    _reset() {
        this.scale = 1;
        this.translateX = 0;
        this.translateY = 0;
        this._applyTransform();
    }

    _applyTransform() {
        this.wrapper.style.transform =
            `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
        this.zoomLabel.textContent = Math.round(this.scale * 100) + "%";
    }

    destroy() {
        document.removeEventListener("keydown", this._keyHandler);
        this.overlay.style.animation = "piz-fade-in 0.15s ease reverse";
        setTimeout(() => {
            if (this.overlay.parentNode) {
                this.overlay.parentNode.removeChild(this.overlay);
            }
        }, 150);
    }
}

// ─── Patch ImageField to open lightbox on click ───────────────────────────────

patch(ImageField.prototype, {
    setup() {
        super.setup(...arguments);
        const root = useRef("root");

        useEffect(() => {
            const el = root.el;
            if (!el) return;

            const onClick = (e) => {
                const img = e.target.closest("img");
                if (!img) return;
                // Only open lightbox if the field is image_1920 / image_128 etc.
                const src = img.src || img.dataset.src;
                if (!src || src.includes("placeholder") || src.endsWith("/")) return;
                e.stopPropagation();
                new ImageZoomLightbox(src);
            };

            el.addEventListener("click", onClick);
            return () => el.removeEventListener("click", onClick);
        });
    },
});
