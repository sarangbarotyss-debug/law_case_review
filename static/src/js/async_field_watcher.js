/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AsyncFieldWatcher extends Component {
    static template = "law_case_review.AsyncFieldWatcher";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.isDestroyed = false;
        this.isPolling = false;

        onMounted(() => this.maybeStartPolling());
        onPatched(() => this.maybeStartPolling());
        onWillUnmount(() => {
            this.isDestroyed = true;
        });
    }

    maybeStartPolling() {
        if (this.isPolling || this.isDestroyed) {
            return;
        }
        if (this.props.record.data[this.props.name]) {
            this.isPolling = true;
            this.pollLoop();
        }
    }

    async pollLoop() {
        const resModel = this.props.record.resModel;
        const resId = this.props.record.resId;
        const fieldName = this.props.name;

        try {
            while (!this.isDestroyed) {
                await new Promise((resolve) => setTimeout(resolve, 2000));
                if (this.isDestroyed) {
                    return;
                }
                let result;
                try {
                    result = await this.orm.read(resModel, [resId], [fieldName]);
                } catch (error) {
                    return;
                }
                if (this.isDestroyed) {
                    return;
                }
                if (result.length === 0 || !result[0][fieldName]) {
                    await this.props.record.load();
                    return;
                }
            }
        } finally {
            this.isPolling = false;
        }
    }
}

registry.category("fields").add("async_field_watcher", {
    component: AsyncFieldWatcher,
});