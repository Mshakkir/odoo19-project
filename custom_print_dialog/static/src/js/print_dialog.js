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
        this.orm          = useService("orm");
        this.iframeRef    = useRef("previewIframe");

        const report = this.props.reportName || "account.report_invoice";
        const id     = this.props.recordId;

        // Standard Odoo URL for iframe preview and print — always works
        this.pdfPreviewUrl = `/report/pdf/${report}/${id}`;
        // Standard Odoo download URL for PDF (with attachment header)
        this.pdfDownloadUrl = `/report/pdf/${report}/${id}?download=true`;

        this.state = useState({
            loading:       true,
            loadError:     false,
            selectedPages: "all",
            customPages:   "",
            layout:        "portrait",
            copies:        1,
            format:        "pdf",
            fileHandle:    null,
            savePath:      "",
            saving:        false,
        });
    }

    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
    onIframeError() { this.state.loading = false; this.state.loadError = true; }

    // ── Choose save location ──────────────────────────────────────────────────
    async onChooseLocation() {
        const isXml = this.state.format === "xml";
        const ext   = isXml ? "xml" : "pdf";
        const mime  = isXml ? "application/xml" : "application/pdf";
        const name  = `${this.props.recordName || "document"}.${ext}`;

        if (window.showSaveFilePicker) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: name,
                    types: [{ description: isXml ? "XML File" : "PDF Document",
                               accept: { [mime]: [`.${ext}`] } }],
                });
                this.state.fileHandle = handle;
                this.state.savePath   = handle.name;
            } catch (err) {
                if (err.name !== "AbortError") console.warn("File picker error:", err);
            }
        } else {
            this.state.savePath = name;
            this.notification.add("Your browser will save to the Downloads folder.", { type: "info" });
        }
    }

    // ── Save ─────────────────────────────────────────────────────────────────
    async onSave() {
        const isXml    = this.state.format === "xml";
        const ext      = isXml ? "xml" : "pdf";
        const fileName = `${this.props.recordName || "document"}.${ext}`;

        this.state.saving = true;
        try {
            let blob;

            if (isXml) {
                // XML: use Odoo's JSON-RPC (guaranteed to work on HTTPS — same
                // session, no cross-origin issues, no custom controller needed)
                const result = await this.orm.call(
                    "ir.actions.report",
                    "get_xml_export",
                    [this.props.reportName, [this.props.recordId]]
                );
                // result is a base64-encoded XML string returned by Python
                const xmlString = result.xml_content || result;
                blob = new Blob([xmlString], { type: "application/xml" });

            } else {
                // PDF: fetch from standard Odoo report URL
                // Use XMLHttpRequest with withCredentials for HTTPS session cookie
                blob = await this._xhrBlob(this.pdfDownloadUrl);
            }

            // Write to chosen location or trigger download
            await this._writeBlob(blob, fileName);

        } catch (err) {
            console.error("Save failed:", err);
            this.notification.add(`Save failed: ${err.message}`, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    // XHR with credentials — works on HTTPS
    _xhrBlob(url) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("GET", url, true);
            xhr.responseType = "blob";
            xhr.withCredentials = true;
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.response);
                } else {
                    reject(new Error(`Server returned ${xhr.status}`));
                }
            };
            xhr.onerror = () => reject(new Error("Network error"));
            xhr.send();
        });
    }

    // Write blob to fileHandle (Chrome) or trigger anchor download (all browsers)
    async _writeBlob(blob, fileName) {
        if (this.state.fileHandle) {
            try {
                const writable = await this.state.fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();
                this.notification.add(`Saved to: ${this.state.fileHandle.name}`,
                    { type: "success" });
                return;
            } catch (err) {
                console.warn("createWritable failed, using download:", err);
            }
        }
        // Blob URL download — no re-request, no "File wasn't available" error
        const blobUrl = URL.createObjectURL(blob);
        const link    = document.createElement("a");
        link.href     = blobUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
        this.notification.add(`Download started`, { type: "success" });
    }

    onPrint() {
        const win = window.open(this.pdfPreviewUrl, "_blank");
        if (!win) {
            this.notification.add("Pop-up blocked. Please allow pop-ups.", { type: "warning" });
            return;
        }
        win.onload = () => setTimeout(() => { win.focus(); win.print(); }, 600);
    }

    onClose() { this.props.close(); }

    get dialogTitle() {
        const label = this.props.docLabel || "Document";
        const name  = this.props.recordName || "";
        return `Print — ${label}${name ? ": " + name : ""}`;
    }

    get saveButtonLabel() {
        if (this.state.saving) return "Saving...";
        return this.state.format === "xml" ? "Save as XML" : "Save as PDF";
    }

    get saveButtonIcon() {
        if (this.state.saving) return "fa fa-spinner fa-spin";
        return this.state.format === "xml" ? "fa fa-code" : "fa fa-file-pdf-o";
    }

    get locationPlaceholder() {
        return `${this.props.recordName || "document"}.${this.state.format}`;
    }

    setFormat(val) {
        this.state.format     = val;
        this.state.savePath   = "";
        this.state.fileHandle = null;
    }
    setPages(val)  { this.state.selectedPages = val; }
    setLayout(val) { this.state.layout = val; }
}

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
