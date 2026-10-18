/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FilterSelect, FilterDate } from "@finance/js/finance_filters";

/**
 * Customer financials report (full screen). One block per customer
 * (student/applicant): the header row shows the Opening Balance (net debt
 * before the period), the period In/Out totals and the Remaining balance;
 * the detail rows below list each operation with only its In/Out value.
 * Filters mirror the operations report: period presets + From/To, customer
 * and type.
 */
export class FinanceCustomerReport extends Component {
    static template = "finance.CustomerReport";
    static components = { FilterSelect, FilterDate };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const ctx = (this.props.action && this.props.action.context) || {};
        this.state = useState({
            loading: true,
            period: ctx.default_period || "all",
            dateFrom: ctx.default_date_from || "",
            dateTo: ctx.default_date_to || "",
            partnerId: false,
            moveType: false,
            hideEmpty: false,
            customers: [],
            partnerOptions: [],
        });
        onWillStart(() => this.load());
    }

    get periodOptions() {
        return [
            { value: "day", label: "Day" },
            { value: "week", label: "Week" },
            { value: "month", label: "Month" },
            { value: "last_3m", label: "Last 3 Months" },
            { value: "last_6m", label: "Last 6 Months" },
            { value: "last_1y", label: "Last Year" },
            { value: "between", label: "Between" },
            { value: "all", label: "All" },
        ];
    }

    get partnerFilterOptions() {
        return [{ value: false, label: "All Students" }, ...this.state.partnerOptions];
    }

    /** Customers visible after the "hide empty" toggle: when on, drop those
     *  with no operation rows matching the current filters. */
    get visibleCustomers() {
        if (!this.state.hideEmpty) {
            return this.state.customers;
        }
        return this.state.customers.filter((c) => c.rows.length > 0);
    }

    toggleHideEmpty() {
        this.state.hideEmpty = !this.state.hideEmpty;
    }

    get typeFilterOptions() {
        return [
            { value: false, label: "All Types" },
            { value: "charge", label: "Debt" },
            { value: "cash_in", label: "Cash In" },
            { value: "cash_out", label: "Cash Out" },
        ];
    }

    async load() {
        if (this.state.period === "between" && !(this.state.dateFrom && this.state.dateTo)) {
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const res = await this.orm.call(
            "finance.student.charge", "get_customer_report",
            [
                this.state.period,
                this.state.dateFrom || null,
                this.state.dateTo || null,
                this.state.partnerId || null,
                this.state.moveType || null,
            ]
        );
        this.state.customers = res.customers;
        this.state.partnerOptions = res.partner_options;
        this.state.loading = false;
    }

    refresh() {
        return this.load();
    }

    async setPeriod(period) {
        this.state.period = period;
        if (period === "between" && !(this.state.dateFrom && this.state.dateTo)) {
            return;
        }
        await this.load();
    }

    async setDate(which, value) {
        if (which === "from") {
            this.state.dateFrom = value;
        } else {
            this.state.dateTo = value;
        }
        if (this.state.period === "between" && this.state.dateFrom && this.state.dateTo) {
            await this.load();
        }
    }

    async setPartner(partnerId) {
        this.state.partnerId = partnerId;
        await this.load();
    }

    async setType(moveType) {
        this.state.moveType = moveType;
        await this.load();
    }

    openPartner(id) {
        if (!id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRecord(model, id) {
        if (!model || !id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("finance.CustomerReport", FinanceCustomerReport);
