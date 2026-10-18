/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ContactNotesWidget extends Component {
    static template = "contact_notes.NotesWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["one2many"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ notes: [] });
        onWillStart(() => this.loadNotes());
    }

    async loadNotes() {
        const id = this.props.record.resId;
        if (!id) return;
        this.state.notes = await this.orm.searchRead(
            "contact.note",
            [["partner_id", "=", id]],
            ["employee_id", "date", "text"],
            { order: "date desc" }
        );
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr.replace(" ", "T") + "Z");
        return d.toLocaleString([], {
            year: "numeric", month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }

    async addNote() {
        const id = this.props.record.resId;
        if (!id) return;
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: "Add Note",
                res_model: "contact.note.wizard",
                views: [[false, "form"]],
                target: "new",
                context: { default_partner_id: id },
            },
            { onClose: () => this.loadNotes() }
        );
    }

    async editNote(note) {
        const id = this.props.record.resId;
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: "Edit Note",
                res_model: "contact.note.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_partner_id: id,
                    default_note_id: note.id,
                    default_text: note.text,
                },
            },
            { onClose: () => this.loadNotes() }
        );
    }

    async deleteNote(noteId) {
        await this.orm.unlink("contact.note", [noteId]);
        await this.loadNotes();
    }
}

registry.category("fields").add("contact_notes_widget", {
    component: ContactNotesWidget,
    supportedTypes: ["one2many"],
});
