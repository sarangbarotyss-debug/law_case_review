/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ClientRequestProgress extends Component {
    static template = "law_case_review.ClientRequestProgress";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            status: "running", // running | failed
        });
        this.isDestroyed = false;

        onMounted(() => {
            this.pollLoop();
        });
        onWillUnmount(() => {
            this.isDestroyed = true;
        });
    }

    async pollLoop() {
        const wizardId = this.props.record.resId;

        while (!this.isDestroyed) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            if (this.isDestroyed) {
                return;
            }

            const wizardData = await this.orm.read(
                "client.request.upload.wizard",
                [wizardId],
                ["client_request_id"]
            );
            const clientRequestId = wizardData[0].client_request_id[0];

            let records;
            try {
                records = await this.orm.read(
                    "law.client.request",
                    [clientRequestId],
                    ["processing_state"]
                );
            } catch (error) {
                records = [];
            }

            if (records.length === 0) {
                // Record was deleted - extraction failed
                await this.orm.call(
                    "client.request.upload.wizard",
                    "action_handle_failure",
                    [[wizardId]]
                );
                this.state.status = "failed";
                this.reopenWizard(wizardId);
                return;
            }

            if (records[0].processing_state === "done") {
                this.env.dialogData?.close();
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "law.client.request",
                    res_id: clientRequestId,
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "current",
                });
                return;
            }
            // still pending - loop continues
        }
    }

    async reopenWizard(wizardId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "client.request.upload.wizard",
            res_id: wizardId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("fields").add("law_client_request_progress", {
    component: ClientRequestProgress,
});