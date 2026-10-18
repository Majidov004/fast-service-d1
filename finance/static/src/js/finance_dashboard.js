/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FilterSelect, FilterDate } from "@finance/js/finance_filters";

export class FinanceDashboard extends Component {
    static template = "finance.Dashboard";
    static components = { FilterSelect, FilterDate };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            overview: null,
            cards: [],
            period: "month",
            dateFrom: "",
            dateTo: "",
            loading: true,
        });

        onWillStart(() => this.loadAll());
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

    async loadAll() {
        this.state.loading = true;
        const df = this.state.dateFrom || null;
        const dt = this.state.dateTo || null;
        const [overview, cards] = await Promise.all([
            this.orm.call("finance.cash.register", "get_overview", [this.state.period, df, dt]),
            this.orm.call("finance.cash.register", "get_dashboard", [this.state.period, df, dt]),
        ]);
        this.state.overview = overview;
        this._stampCardRange(cards);
        this.state.cards = cards;
        this.state.loading = false;
    }

    // ── Global period (drives the cards too) ─────────────────────────────────
    _stampCardRange(cards) {
        // keep each card's date inputs in sync with the global range (Between)
        if (this.state.period === "between") {
            cards.forEach((c) => {
                c.date_from = this.state.dateFrom;
                c.date_to = this.state.dateTo;
            });
        }
    }

    async reloadOverview() {
        this.state.overview = await this.orm.call(
            "finance.cash.register", "get_overview",
            [this.state.period, this.state.dateFrom || null, this.state.dateTo || null]
        );
    }

    async reloadAllCards() {
        // All cards follow the global period/range. Individual cards can still
        // be overridden afterwards; the next global change re-syncs them all.
        const cards = await this.orm.call(
            "finance.cash.register", "get_dashboard",
            [this.state.period, this.state.dateFrom || null, this.state.dateTo || null]
        );
        this._stampCardRange(cards);
        this.state.cards = cards;
    }

    async _reloadGlobal() {
        await Promise.all([this.reloadOverview(), this.reloadAllCards()]);
    }

    async setOverviewPeriod(period) {
        this.state.period = period;
        // "Between" waits until both dates are chosen.
        if (period === "between" && !(this.state.dateFrom && this.state.dateTo)) {
            return;
        }
        await this._reloadGlobal();
    }

    async setGlobalDate(which, value) {
        if (which === "from") {
            this.state.dateFrom = value;
        } else {
            this.state.dateTo = value;
        }
        if (this.state.period === "between" && this.state.dateFrom && this.state.dateTo) {
            await this._reloadGlobal();
        }
    }

    // ── Per-card period ──────────────────────────────────────────────────────
    _card(cardId) {
        const idx = this.state.cards.findIndex((c) => c.id === cardId);
        return idx === -1 ? null : this.state.cards[idx];
    }

    async reloadCard(card) {
        const data = await this.orm.call(
            "finance.cash.register", "get_card_data",
            [[card.id], card.period, card.date_from || null, card.date_to || null]
        );
        // keep the client-side custom range across the payload replacement
        data.date_from = card.date_from || "";
        data.date_to = card.date_to || "";
        const idx = this.state.cards.findIndex((c) => c.id === card.id);
        if (idx !== -1) {
            this.state.cards[idx] = data;
        }
    }

    setCardPeriod(card, period) {
        const c = this._card(card.id);
        if (!c) {
            return;
        }
        c.period = period;
        if (period === "between" && !(c.date_from && c.date_to)) {
            return; // reveal date inputs, wait for both
        }
        this.reloadCard(c);
    }

    setCardDate(card, which, value) {
        const c = this._card(card.id);
        if (!c) {
            return;
        }
        if (which === "from") {
            c.date_from = value;
        } else {
            c.date_to = value;
        }
        if (c.period === "between" && c.date_from && c.date_to) {
            this.reloadCard(c);
        }
    }

    openMove(id) {
        if (!id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "finance.cash.move",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openDetailed() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "finance.OperationsReport",
            name: "Operations Detail",
            context: {
                default_period: this.state.period,
                default_date_from: this.state.dateFrom || false,
                default_date_to: this.state.dateTo || false,
            },
        });
    }

    refresh() {
        return this.loadAll();
    }
}

registry.category("actions").add("finance.Dashboard", FinanceDashboard);
