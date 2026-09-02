/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup(){
        super.setup();
        this.actionService = useService("action");
    },
    get showUploadButton(){
        return this.props.resModel === "law.client.request";
    },
    async onUploadDocument(){
        await this.actionService.doAction("law_case_review.action_client_request_upload_wizard")
    }
})