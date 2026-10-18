/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FilterSelect, FilterDate } from "@finance/js/finance_filters";

/**
 * Detailed operations report (full screen). Per cash register it lists every
 * confirmed cash move + transfer in the period, ordered by date, with the
 * running balance after each operation (register currency). Filters: period
 * (same presets as the dashboard) + register.
 */
export class FinanceOperationsReport extends Component {
    static template = "finance.OperationsReport";
    static components = { FilterSelect, FilterDate };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const ctx = (this.props.action && this.props.action.context) || {};
        this.state = useState({
            loading: true,
            period: ctx.default_period || "month",
            dateFrom: ctx.default_date_from || "",
            dateTo: ctx.default_date_to || "",
            registerId: false,
            categoryId: false,
            registers: [],
            registerOptions: [],
            categoryOptions: [],
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

    get registerFilterOptions() {
        return [{ value: false, label: "All Registers" }, ...this.state.registerOptions];
    }

    get categoryFilterOptions() {
        return [{ value: false, label: "All Categories" }, ...this.state.categoryOptions];
    }

    async load() {
        if (this.state.period === "between" && !(this.state.dateFrom && this.state.dateTo)) {
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const res = await this.orm.call(
            "finance.cash.register", "get_operations_report",
            [
                this.state.period,
                this.state.dateFrom || null,
                this.state.dateTo || null,
                this.state.registerId || null,
                this.state.categoryId || null,
            ]
        );
        this.state.registers = res.registers;
        this.state.registerOptions = res.register_options;
        this.state.categoryOptions = res.category_options;
        this.state.loading = false;
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

    async setRegister(registerId) {
        this.state.registerId = registerId;
        await this.load();
    }

    async setCategory(categoryId) {
        this.state.categoryId = categoryId;
        await this.load();
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

registry.category("actions").add("finance.OperationsReport", FinanceOperationsReport);
