/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MeetingCommentsWidget extends Component {
    static template = "contact_customization.MeetingCommentsWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["one2many"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ groups: [] });
        onWillStart(() => this.loadComments());
    }

    async loadComments() {
        const id = this.props.record.resId;
        if (!id) {
            this.state.groups = [];
            return;
        }
        this.state.groups = await this.orm.call(
            "res.partner",
            "get_meeting_comments",
            [[id]]
        );
    }
}

registry.category("fields").add("meeting_comments_widget", {
    component: MeetingCommentsWidget,
    supportedTypes: ["one2many"],
});
