/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class EmbeddingReembedProgress extends Component {
    static template = "law_case_review.EmbeddingReembedProgress";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            total: 0,
            done: 0,
            errors: 0,
            status: "idle", // idle | running | done
        });

        onWillStart(async () => {
            this.state.total = this.props.record.data.total_count || 0;
            this.state.done = this.props.record.data.done_count || 0;
            if (this.state.total > 0) {
                this.state.status = "running";
                // await this.runBatches();
            } else {
                this.state.status = "done";
            }
        });

        onMounted(() => {
            if (this.state.status === "running") {
                this.runBatches();
            } else if (this.state.status === "done") {
                this.closeAfterCompletion();
            }
        });
    }

    async runBatches() {
        const resId = this.props.record.resId;
        try {
            while (this.state.status === "running") {
                const result = await this.orm.call(
                    "law.embedding.model.change.wizard",
                    "action_process_batch",
                    [[resId]],
                    { batch_size: 5 }
                );
                this.state.done = result.done_count;
                this.state.errors = result.error_count;
                if (result.is_complete) {
                    this.state.status = "done";
                    this.closeAfterCompletion();
                    break;
                }
                await new Promise((resolve) => setTimeout(resolve, 500));
            }
        } catch (error) {
            console.error("Re-embedding failed:", error);
            this.state.status = "done";
        }
    }

    get progressPercent() {
        if (!this.state.total) return 0;
        return Math.round((this.state.done / this.state.total) * 100);
    }

    closeAfterCompletion() {
        setTimeout(() => {
            this.env.dialogData?.close();
        }, 1200);
    }
}

registry.category("fields").add("law_reembed_progress", {
    component: EmbeddingReembedProgress,
});