/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useState, useSubEnv, useEffect } from "@odoo/owl";
import { CaseQAPanel } from "./case_qa_panel";
patch(FormController, {
    components: { ...FormController.components, CaseQAPanel },
});
patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === "law.case") {
            this.caseQAState = useState({
                open: false,
                dragged: false,
                positioned: false,
                x: 0,
                y: 0,
            });
            useSubEnv({ caseQAState: this.caseQAState });
            useEffect(
                (open) => {
                    document.body.classList.toggle("o_case_qa_open", !!open);
                    return () => document.body.classList.remove("o_case_qa_open");
                },
                () => [this.caseQAState.open]
            );
            useEffect(
                () => {
                    const onResize = () => {
                        const state = this.caseQAState;
                        if (!state.positioned) {
                            return;
                        }
                        state.x = Math.min(Math.max(state.x, 10), window.innerWidth - 70);
                        state.y = Math.min(Math.max(state.y, 10), window.innerHeight - 70);
                    };
                    window.addEventListener("resize", onResize);
                    return () => window.removeEventListener("resize", onResize);
                },
                () => []
            );
        }
    },
    get showCaseQAIcon() {
        return this.props.resModel === "law.case"
            && this.caseQAState
            && !!this.model.root.resId
            && !this.caseQAState.open;
    },
    get showCaseQAPanel() {
        return this.props.resModel === "law.case"
            && this.caseQAState
            && this.caseQAState.open;
    },
    onClickCaseQAIcon() {
        if (this.caseQAState.dragged) {
            this.caseQAState.dragged = false;
            return;
        }
        this.caseQAState.open = true;
    },
    onCaseQAIconPointerDown(ev) {
        const state = this.caseQAState;
        const startX = ev.clientX;
        const startY = ev.clientY;
        const startLeft = state.positioned ? state.x : window.innerWidth - 80;
        const startTop = state.positioned ? state.y : window.innerHeight - 120;
        state.dragged = false;
        const onMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            const dy = moveEv.clientY - startY;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                state.dragged = true;
            }
            state.positioned = true;
            state.x = Math.min(Math.max(startLeft + dx, 10), window.innerWidth - 70);
            state.y = Math.min(Math.max(startTop + dy, 10), window.innerHeight - 70);
        };
        const onUp = () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    },
});