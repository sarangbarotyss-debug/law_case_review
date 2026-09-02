/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useState, useSubEnv, onMounted, useEffect} from "@odoo/owl";
import { DocumentPreviewPanel } from "./document_preview_panel";

patch(FormController, {
    components: { ...FormController.components, DocumentPreviewPanel },
});

patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === "law.client.request") {
            this.documentPreviewState = useState({ open: false });
            useSubEnv({ documentPreviewState: this.documentPreviewState });
            useEffect(
                (open) => {
                    document.body.classList.toggle("o_document_preview_open", !!open);
                    return () => document.body.classList.remove("o_document_preview_open");
                },
                () => [this.documentPreviewState.open]
            );
            onMounted(() => {
                const hasFile = this.model.root && this.model.root.data && this.model.root.data.file_name;
                if (hasFile) {
                    this.documentPreviewState.open = true;
                }
            });
        }
    },
    get showPreviewButton() {
        return this.props.resModel === "law.client.request"
            && this.documentPreviewState
            && !this.documentPreviewState.open;
    },
    get showPreviewPanel() {
        return this.props.resModel === "law.client.request"
            && this.documentPreviewState
            && this.documentPreviewState.open;
    },
    onClickPreview() {
        if (this.documentPreviewState) {
            this.documentPreviewState.open = true;
        }
    },
});