/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillRender, useState } from "@odoo/owl";
import { standardFieldProps } from '@web/views/fields/standard_field_props';

export class DocumentPreviewPanel extends Component {
    static template = "law_case_review.DocumentPreviewPanel";
    static props = ["resModel", "resId?", "fileName?"];

    setup(){
        this.zoomState = useState({'level':1});
    }
    zoomIn(){
        this.zoomState.level = Math.min(this.zoomState.level + 0.25, 3);
        
    }
    zoomOut(){
        this.zoomState.level = Math.max(this.zoomState.level - 0.25, 0.5);
        
    }
    zoomReset(){
        this.zoomState.level = 1;
        
    }

    _applyZoomToIframe(){
        const iframe = document.querySelector(".o_document_preview_panel iframe");
        if (iframe) {
            iframe.src = this.pdfUrl;
        }
    }

    get zoomStyle() {
        return `transform: scale(${this.zoomState.level}); transform-origin: top left;`;
    }
    closePanel() {
        if (this.env.documentPreviewState) {
            this.env.documentPreviewState.open = false;
        }
    }
    get hasFile() {
        return !!this.props.fileName;
    }
    get fileUrl() {
        return `/web/content/${this.props.resModel}/${this.props.resId}/file`;
    }
    get pdfUrl() {
        const encodedFile = encodeURIComponent(this.fileUrl);
        return `/law_case_review/static/lib/web/viewer.html?file=${encodedFile}#zoom=${Math.round(this.zoomState.level * 100)}`;
    }
    get isPdf() {
        return this.props.fileName && this.props.fileName.toLowerCase().endsWith(".pdf");
    }
    get isImage() {
        return this.props.fileName && /\.(png|jpe?g|gif|webp)$/i.test(this.props.fileName);
    }
}

function record_file_name(record) {
    return record.data.file_name || "";
}

registry.category("fields").add("document_preview_panel", {
    component: DocumentPreviewPanel,
});