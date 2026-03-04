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
        this.pdfPreviewUrl  = `/custom_print/report/pdf/${report}/${this.props.recordId}`;
        this.pdfDownloadUrl = `${this.pdfPreviewUrl}?download=true`;
        this.xmlDownloadUrl = `/custom_print/report/xml/${report}/${this.props.recordId}`;

        this.state = useState({
            loading:        true,
            loadError:      false,
            selectedPages:  "all",
            customPages:    "",
            layout:         "portrait",
            copies:         1,
            // "pdf" or "xml"
            format:         "pdf",
            // Chosen save path shown in the location input (display only)
            savePath:       "",
        });
    }

    // ── Iframe events ─────────────────────────────────────────────────────────
    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
    onIframeError() { this.state.loading = false; this.state.loadError = true; }

    // ── File / folder picker ──────────────────────────────────────────────────
    /**
     * Uses the browser's native File System Access API (showSaveFilePicker)
     * when available (Chrome/Edge 86+). Falls back to a standard anchor
     * download for Firefox / Safari.
     *
     * This IS the "destination location" picker — the user sees a native
     * OS save-dialog to choose folder + filename before the file is written.
     */
    async onSave() {
        const isXml    = this.state.format === "xml";
        const ext      = isXml ? "xml"  : "pdf";
        const mime     = isXml ? "application/xml" : "application/pdf";
        const url      = isXml ? this.xmlDownloadUrl : this.pdfDownloadUrl;
        const baseName = `${this.props.recordName || "document"}.${ext}`;

        // ── Modern path: showSaveFilePicker (Chrome / Edge) ──────────────────
        if (window.showSaveFilePicker) {
            try {
                const fileHandle = await window.showSaveFilePicker({
                    suggestedName: baseName,
                    types: [{
                        description: isXml ? "XML File" : "PDF Document",
                        accept: { [mime]: [`.${ext}`] },
                    }],
                });

                // Show chosen path in the input field
                this.state.savePath = fileHandle.name;

                // Fetch the file content and write it
                const response = await fetch(url);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const blob       = await response.blob();
                const writable   = await fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();

                this.notification.add(
                    `${ext.toUpperCase()} saved to: ${fileHandle.name}`,
                    { type: "success", sticky: false }
                );
                return;

            } catch (err) {
                // User cancelled the picker → AbortError, silently ignore
                if (err.name === "AbortError") return;
                // Any other error → fall through to anchor download
                console.warn("showSaveFilePicker failed, falling back:", err);
            }
        }

        // ── Fallback path: anchor download (Firefox / Safari) ────────────────
        // Browser will show its own "Save As" dialog or download bar.
        const link    = document.createElement("a");
        link.href     = url;
        link.download = baseName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.state.savePath = baseName;
        this.notification.add(
            `${ext.toUpperCase()} download started`,
            { type: "success", sticky: false }
        );
    }

    /** Print button — opens PDF in new tab and triggers OS print dialog */
    onPrint() {
        const printWin = window.open(this.pdfPreviewUrl, "_blank");
        if (!printWin) {
            this.notification.add(
                "Pop-up blocked. Please allow pop-ups and try again.",
                { type: "warning" }
            );
            return;
        }
        printWin.onload = () => setTimeout(() => { printWin.focus(); printWin.print(); }, 600);
    }

    onClose() { this.props.close(); }

    // ── Helpers ───────────────────────────────────────────────────────────────
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
        const ext = this.state.format === "xml" ? "xml" : "pdf";
        return `${this.props.recordName || "document"}.${ext}`;
    }

    setFormat(val)  { this.state.format = val; this.state.savePath = ""; }
    setPages(val)   { this.state.selectedPages = val; }
    setLayout(val)  { this.state.layout = val; }
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
