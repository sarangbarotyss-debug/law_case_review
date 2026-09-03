/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CaseQAPanel extends Component {
    static template = "law_case_review.CaseQAPanel";
    static props = ["resId"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            question: "",
            asking: false,
            messages: [],
        });
        onWillStart(async () => {
            await this.loadHistory();
        });
    }

    async loadHistory() {
        const logs = await this.orm.searchRead(
            "law.case.qa.log",
            [["case_id", "=", this.props.resId], ["hidden_from_chat", "=", false]],
            ["question", "answer", "create_date"],
            { order: "create_date asc", limit: 20 }
        );
        this.state.messages = logs.map((log) => ({
            question: log.question,
            answer: log.answer,
        }));
    }

    async onClickAsk() {
        if (!this.state.question.trim() || this.state.asking) return;
        const question = this.state.question;
        this.state.question = "";
        this.state.asking = true;
        this.state.messages.push({ question, answer: null });
        try {
            const result = await this.orm.call(
                "law.case",
                "action_ask_case_question",
                [[this.props.resId], question]
            );
            if (result.from_cache) {
                this.state.messages[this.state.messages.length - 1].answer = result.answer;
            } else {
                await this.loadHistory();
            }
            if (this.env.caseFormModel) {
                await this.env.caseFormModel.root.load();
            }
        } finally {
            this.state.asking = false;
        }
    }
    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.onClickAsk();
        }
    }

    onInputResize(ev) {
        const el = ev.target;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }

    async onClickClearChat() {
        await this.orm.call(
            "law.case",
            "action_clear_case_qa",
            [[this.props.resId]]
        );
        this.state.messages = [];
    }

    closePanel() {
        if (this.env.caseQAState) {
            this.env.caseQAState.open = false;
        }
    }
}

registry.category("fields").add("case_qa_panel", {
    component: CaseQAPanel,
});