/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, useRef } from "@odoo/owl";

export class PrintPreviewDialog extends Component {
    static template = "custom_print_dialog.PrintPreviewDialog";
    static components = { Dialog };
    static props = {
        recordId:   { type: Number },
        recordName: { type: String, optional: true },
        reportName: { type: String, optional: true },
        docLabel:   { type: String, optional: true },
        close:      { type: Function },
    };

    setup() {
        this.notification = useService("notification");
        this.iframeRef    = useRef("previewIframe");

        const report = this.props.reportName || "account.report_invoice";
        const id     = this.props.recordId;

        // ── Odoo's standard PDF URL for the iframe preview ───────────────────
        // This always works for any report — it is the same URL Odoo uses
        // internally when you click Print normally.
        this.pdfPreviewUrl = `/report/pdf/${report}/${id}`;

        // ── Custom controller URLs for Save (query-param form, no dot issues) ─
        const base          = `/custom_print/report/pdf?report_name=${encodeURIComponent(report)}&record_id=${id}`;
        this.pdfDownloadUrl = `${base}&download=true`;
        this.xmlDownloadUrl = `/custom_print/report/xml?report_name=${encodeURIComponent(report)}&record_id=${id}`;

        this.state = useState({
            loading:       true,
            loadError:     false,
            selectedPages: "all",
            customPages:   "",
            layout:        "portrait",
            copies:        1,
            format:        "pdf",   // "pdf" or "xml"
            savePath:      "",
        });
    }

    // ── Iframe events ─────────────────────────────────────────────────────────
    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
    onIframeError() { this.state.loading = false; this.state.loadError = true; }

    // ── Save with OS file picker ──────────────────────────────────────────────
    async onSave() {
        const isXml   = this.state.format === "xml";
        const ext     = isXml ? "xml" : "pdf";
        const mime    = isXml ? "application/xml" : "application/pdf";
        const url     = isXml ? this.xmlDownloadUrl : this.pdfDownloadUrl;
        const base    = `${this.props.recordName || "document"}.${ext}`;

        // Chrome/Edge 86+: native OS Save As dialog
        if (window.showSaveFilePicker) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: base,
                    types: [{ description: isXml ? "XML File" : "PDF Document",
                               accept: { [mime]: [`.${ext}`] } }],
                });
                this.state.savePath = handle.name;
                const resp     = await fetch(url);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const blob     = await resp.blob();
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                this.notification.add(
                    `${ext.toUpperCase()} saved: ${handle.name}`,
                    { type: "success", sticky: false }
                );
                return;
            } catch (err) {
                if (err.name === "AbortError") return;
                console.warn("showSaveFilePicker failed, falling back:", err);
            }
        }

        // Firefox / Safari fallback: standard anchor download
        const link    = document.createElement("a");
        link.href     = url;
        link.download = base;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.state.savePath = base;
        this.notification.add(
            `${ext.toUpperCase()} download started`,
            { type: "success", sticky: false }
        );
    }

    // Print: open the standard Odoo PDF URL in new tab → OS print dialog
    onPrint() {
        const win = window.open(this.pdfPreviewUrl, "_blank");
        if (!win) {
            this.notification.add(
                "Pop-up blocked. Please allow pop-ups and try again.",
                { type: "warning" }
            );
            return;
        }
        win.onload = () => setTimeout(() => { win.focus(); win.print(); }, 600);
    }

    onClose() { this.props.close(); }

    // ── Computed helpers ──────────────────────────────────────────────────────
    get dialogTitle() {
        const label = this.props.docLabel || "Document";
        const name  = this.props.recordName || "";
        return `Print — ${label}${name ? ": " + name : ""}`;
    }

    get saveButtonLabel() {
        return this.state.format === "xml" ? "Save as XML" : "Save as PDF";
    }
    get saveButtonIcon() {
        return this.state.format === "xml" ? "fa fa-code" : "fa fa-file-pdf-o";
    }
    get locationPlaceholder() {
        return `${this.props.recordName || "document"}.${this.state.format}`;
    }

    setFormat(val) { this.state.format = val; this.state.savePath = ""; }
    setPages(val)  { this.state.selectedPages = val; }
    setLayout(val) { this.state.layout = val; }
}

// ── Register client action ────────────────────────────────────────────────────
registry.category("actions").add(
    "custom_print_dialog.open_print_dialog",
    async (env, action) => {
        const { record_id, record_name, report_name, doc_label } = action.params || {};
        env.services.dialog.add(PrintPreviewDialog, {
            recordId:   record_id,
            recordName: record_name,
            reportName: report_name,
            docLabel:   doc_label,
        });
    }
);








///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { Dialog } from "@web/core/dialog/dialog";
//import { Component, useState, onMounted, useRef } from "@odoo/owl";
//
///**
// * PrintPreviewDialog
// *
// * Split-screen dialog:
// *   LEFT  → Existing PDF report rendered in an <iframe> (the same PDF Odoo generates)
// *   RIGHT → Print settings: Pages, Layout, Copies
// *   BOTTOM (inside right panel) → "Save as PDF" (download) + "Print" (system printer)
// *
// * Works for ALL move types: out_invoice, in_invoice, out_refund, in_refund,
// * out_receipt, in_receipt, and journal entries (entry).
// */
//export class PrintPreviewDialog extends Component {
//    static template = "custom_print_dialog.PrintPreviewDialog";
//    static components = { Dialog };
//    static props = {
//        recordId:   { type: Number },
//        recordName: { type: String, optional: true },
//        reportName: { type: String, optional: true },
//        docLabel:   { type: String, optional: true },
//        close:      { type: Function },
//    };
//
//    setup() {
//        this.notification = useService("notification");
//        this.iframeRef    = useRef("previewIframe");
//
//        // Default report: account.report_invoice covers all invoice types.
//        // For journal entries the server sends account.report_move_template.
//        const report = this.props.reportName || "account.report_invoice";
//
//        // Odoo's report URL pattern: /report/pdf/<report_name>/<id>
//        // The browser renders the PDF natively inside the iframe.
//        this.pdfPreviewUrl = `/report/pdf/${report}/${this.props.recordId}`;
//        this.pdfDownloadUrl = `${this.pdfPreviewUrl}?download=true`;
//
//        this.state = useState({
//            loading:       true,
//            loadError:     false,
//            selectedPages: "all",
//            customPages:   "",
//            layout:        "portrait",
//            copies:        1,
//        });
//    }
//
//    // ── Iframe events ────────────────────────────────────────────────────────
//
//    onIframeLoad() {
//        this.state.loading   = false;
//        this.state.loadError = false;
//    }
//
//    onIframeError() {
//        this.state.loading   = false;
//        this.state.loadError = true;
//    }
//
//    // ── Actions ──────────────────────────────────────────────────────────────
//
//    /**
//     * Save as PDF — triggers the browser's native file download.
//     * Uses Odoo's ?download=true flag which sets Content-Disposition: attachment.
//     */
//    onDownloadPDF() {
//        const link = document.createElement("a");
//        link.href     = this.pdfDownloadUrl;
//        link.download = `${this.props.recordName || "document"}.pdf`;
//        document.body.appendChild(link);
//        link.click();
//        document.body.removeChild(link);
//
//        this.notification.add("PDF download started", { type: "success", sticky: false });
//    }
//
//    /**
//     * Print — opens the PDF in a new tab and immediately triggers the
//     * browser's system print dialog (Ctrl+P equivalent).
//     */
//    onPrint() {
//        const printWin = window.open(this.pdfPreviewUrl, "_blank");
//        if (!printWin) {
//            this.notification.add(
//                "Pop-up blocked. Please allow pop-ups and try again.",
//                { type: "warning" }
//            );
//            return;
//        }
//        // Wait for the PDF to load before triggering print
//        printWin.onload = () => {
//            setTimeout(() => {
//                printWin.focus();
//                printWin.print();
//            }, 600);
//        };
//    }
//
//    onClose() {
//        this.props.close();
//    }
//
//    // ── Helpers ──────────────────────────────────────────────────────────────
//
//    get dialogTitle() {
//        const label = this.props.docLabel || "Document";
//        const name  = this.props.recordName || "";
//        return `Print — ${label}${name ? ": " + name : ""}`;
//    }
//
//    setPages(val) {
//        this.state.selectedPages = val;
//    }
//
//    setLayout(val) {
//        this.state.layout = val;
//    }
//}
//
//// ── Register the client action ────────────────────────────────────────────────
//
//registry.category("actions").add(
//    "custom_print_dialog.open_print_dialog",
//    async (env, action) => {
//        const { record_id, record_name, report_name, doc_label } = action.params || {};
//        env.services.dialog.add(PrintPreviewDialog, {
//            recordId:   record_id,
//            recordName: record_name,
//            reportName: report_name,
//            docLabel:   doc_label,
//        });
//    }
//);
//
