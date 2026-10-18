/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Applicant Analytics report (inside Staff Dashboard). For the current month
 * it shows how many applicants are at each funnel stage (side-by-side cards)
 * with a small percentage change vs the previous month underneath — so the
 * weak stage (where applicants drop off) is easy to spot.
 */
export class StaffAnalytics extends Component {
    static template = "staff_dashboard.Analytics";

    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call(
            "user.login.log",
            "get_applicant_analytics",
            []
        );
        this.state.loading = false;
    }

    async refresh() {
        this.state.loading = true;
        await this.load();
    }

    // 6-aylıq trend sütunlarının hündürlüyü (ən böyük "registered"-ə görə miqyas)
    get trendMax() {
        const t = (this.state.data && this.state.data.trend) || [];
        return Math.max(1, ...t.map((m) => m.registered));
    }
    barH(v) {
        return Math.round((v / this.trendMax) * 100);
    }
}

registry.category("actions").add("staff_dashboard.Analytics", StaffAnalytics);
