/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";

const RESULTS = [
    { value: "zeif", label: "Weak", btn: "danger" },
    { value: "orta", label: "Average", btn: "warning" },
    { value: "ela", label: "Excellent", btn: "success" },
];

/**
 * Popup dialog: pick a student, answer the exam questions on the left (pulled
 * from the shared Question Bank) and set the result + comment on the right. "Complete Exam" saves everything, marks the exam
 * done and triggers the weak-result notifications; an already-done exam shows
 * "Save Changes" instead (no re-notification).
 */
export class ExamDialog extends Component {
    static template = "training_exam.ExamDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        groupId: Number,
        examId: Number,
        onSaved: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.results = RESULTS;
        this.state = useState({
            loading: true,
            saving: false,
            exam: null,
            selectedLineId: null,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const detail = await this.orm.call(
            "training.group",
            "get_exam_detail",
            [[this.props.groupId], this.props.examId]
        );
        this.state.exam = detail;
        if (detail.students && detail.students.length) {
            this.state.selectedLineId = detail.students[0].line_id;
        }
        this.state.loading = false;
    }

    get selectedStudent() {
        if (!this.state.exam) {
            return null;
        }
        return this.state.exam.students.find(
            (s) => s.line_id === this.state.selectedLineId
        );
    }

    get dialogTitle() {
        return this.state.exam ? this.state.exam.name : "Exam";
    }

    get saveLabel() {
        if (this.state.exam && this.state.exam.state === "done") {
            return "Save Changes";
        }
        return "Complete Exam";
    }

    selectStudent(lineId) {
        this.state.selectedLineId = lineId;
    }

    setResult(value) {
        const student = this.selectedStudent;
        if (student) {
            student.result = value;
        }
    }

    onAnswer(answer, ev) {
        answer.answer = ev.target.value;
    }

    onNote(ev) {
        const student = this.selectedStudent;
        if (student) {
            student.note = ev.target.value;
        }
    }

    async onSave() {
        if (this.state.saving || !this.state.exam) {
            return;
        }
        this.state.saving = true;
        const exam = this.state.exam;
        const payload = {
            complete: exam.state !== "done",
            students: exam.students.map((s) => ({
                line_id: s.line_id,
                result: s.result || false,
                note: s.note || "",
                answers: (s.answers || []).map((a) => ({
                    answer_id: a.answer_id,
                    answer: a.answer || "",
                })),
            })),
        };
        try {
            await this.orm.call(
                "training.group",
                "save_exam",
                [[this.props.groupId], this.props.examId, payload]
            );
            if (this.props.onSaved) {
                await this.props.onSaved();
            }
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}

/**
 * Field widget mounted on the Exam tab. Renders this group's auto-generated
 * exams as mini cards. Clicking a card opens the dialog. No manual creation.
 */
export class TrainingExamWidget extends Component {
    static template = "training_exam.TrainingExamWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ exams: [] });
        onWillStart(() => this.loadExams());
    }

    async loadExams() {
        const id = this.props.record.resId;
        if (!id) {
            this.state.exams = [];
            return;
        }
        this.state.exams = await this.orm.call(
            "training.group",
            "get_exam_cards",
            [[id]]
        );
    }

    openExam(exam) {
        const id = this.props.record.resId;
        if (!id) {
            return;
        }
        this.dialog.add(ExamDialog, {
            groupId: id,
            examId: exam.id,
            onSaved: () => this.loadExams(),
        });
    }
}

registry.category("fields").add("training_exam_widget", {
    component: TrainingExamWidget,
    supportedTypes: ["char"],
});
