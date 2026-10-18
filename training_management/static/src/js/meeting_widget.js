/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/**
 * Popup dialog: edit a single lesson's notes + per-student attendance/comment.
 * Students are handled one at a time (select a student, then set present/absent
 * and write a comment). "Complete Lesson" saves everything and marks the lesson
 * completed; an already-completed lesson shows "Save Changes" instead.
 */
export class MeetingLessonDialog extends Component {
    static template = "training_management.MeetingLessonDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        groupId: Number,
        lessonId: Number,
        onSaved: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            saving: false,
            lesson: null,
            selectedLineId: null,
            askNextTopic: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const detail = await this.orm.call(
            "training.group",
            "get_meeting_lesson_detail",
            [[this.props.groupId], this.props.lessonId]
        );
        this.state.lesson = detail;
        if (detail.students && detail.students.length) {
            this.state.selectedLineId = detail.students[0].line_id;
        }
        this.state.loading = false;
    }

    get selectedStudent() {
        if (!this.state.lesson) {
            return null;
        }
        return this.state.lesson.students.find(
            (s) => s.line_id === this.state.selectedLineId
        );
    }

    get dialogTitle() {
        return this.state.lesson ? this.state.lesson.name : "Meeting";
    }

    get saveLabel() {
        if (this.state.lesson && this.state.lesson.state === "completed") {
            return "Save Changes";
        }
        return "Complete Lesson";
    }

    selectStudent(lineId) {
        this.state.selectedLineId = lineId;
    }

    setAttendance(value) {
        const student = this.selectedStudent;
        if (student) {
            student.attendance = value;
        }
    }

    onComment(ev) {
        const student = this.selectedStudent;
        if (student) {
            student.comment = ev.target.value;
        }
    }

    onTeacherComment(ev) {
        if (this.state.lesson) {
            this.state.lesson.teacher_comment = ev.target.value;
        }
    }

    async onSave() {
        if (this.state.saving || !this.state.lesson) {
            return;
        }
        // First completion → ask whether a new topic runs tomorrow.
        if (this.state.lesson.state !== "completed" && !this.state.askNextTopic) {
            this.state.askNextTopic = true;
            return;
        }
        // Editing an already-completed lesson never spawns an extra lesson.
        await this._doSave(true);
    }

    backFromQuestion() {
        this.state.askNextTopic = false;
    }

    async confirmNextTopic(nextTopic) {
        this.state.askNextTopic = false;
        await this._doSave(nextTopic);
    }

    async _doSave(nextTopic) {
        if (this.state.saving || !this.state.lesson) {
            return;
        }
        this.state.saving = true;
        const lesson = this.state.lesson;
        const payload = {
            teacher_comment: lesson.teacher_comment || "",
            complete: lesson.state !== "completed",
            next_topic: nextTopic !== false,
            students: lesson.students.map((s) => ({
                line_id: s.line_id,
                attendance: s.attendance,
                comment: s.comment || "",
            })),
        };
        try {
            await this.orm.call(
                "training.group",
                "save_meeting_lesson",
                [[this.props.groupId], this.props.lessonId, payload]
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
 * Field widget mounted on the Meeting tab. Renders this group's lessons as mini
 * cards (completed lessons appear dimmed). Clicking a card opens the dialog.
 */
export class TrainingMeetingWidget extends Component {
    static template = "training_management.TrainingMeetingWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ lessons: [] });
        onWillStart(() => this.loadLessons());
    }

    async loadLessons() {
        const id = this.props.record.resId;
        if (!id) {
            this.state.lessons = [];
            return;
        }
        this.state.lessons = await this.orm.call(
            "training.group",
            "get_meeting_lessons",
            [[id]]
        );
    }

    openLesson(lesson) {
        const id = this.props.record.resId;
        if (!id) {
            return;
        }
        this.dialog.add(MeetingLessonDialog, {
            groupId: id,
            lessonId: lesson.id,
            onSaved: () => this.loadLessons(),
        });
    }

    deleteLesson(lesson, ev) {
        ev.stopPropagation();
        const id = this.props.record.resId;
        if (!id) {
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Extra Lesson",
            body: `“${lesson.name}” will be deleted and the following lessons will shift back by one slot. Continue?`,
            confirmLabel: "Delete",
            confirm: async () => {
                this.state.lessons = await this.orm.call(
                    "training.group",
                    "delete_extra_lesson",
                    [[id], lesson.id]
                );
            },
            cancel: () => {},
        });
    }
}

registry.category("fields").add("training_meeting_widget", {
    component: TrainingMeetingWidget,
    supportedTypes: ["char"],
});
