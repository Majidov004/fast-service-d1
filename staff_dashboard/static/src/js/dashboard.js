/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { FilterSelect, FilterMultiSelect, FilterDate } from "./filter_widgets";

class StaffDashboard extends Component {
    static template = "staff_dashboard.Dashboard";
    static components = { FilterSelect, FilterMultiSelect, FilterDate };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.state = useState({
            comments: [],
            activity: [],
            loadingComments: true,
            loadingActivity: true,
            expanded: {},
            latestOnly: true,   // default: hər istifadəçinin yalnız sonuncu günü
            showFilters: false, // Notes & Comments filter paneli açıq/bağlı
            activitySearch: '', // User Activity — istifadəçi adına görə axtarış
            filters: {
                text: '',
                // çoxseçimli filtrlər — massiv (OR daxili, AND filtrlər arası)
                author: [],
                student_id: [],
                teacher_id: [],
                group_id: [],
                source: [],
                date_mode: 'all',   // all | year | month | week | between | day
                date_from: '',
                date_to: '',
                date_one: '',
            },
            filterOptions: { authors: [], students: [], teachers: [], groups: [], sources: [] },
        });
        onWillStart(async () => {
            await Promise.all([this.loadComments(), this.loadActivity()]);
        });
    }

    toggleRow(key) {
        this.state.expanded[key] = !this.state.expanded[key];
    }

    toggleLatestOnly() {
        this.state.latestOnly = !this.state.latestOnly;
    }

    setActivitySearch(value) {
        this.state.activitySearch = value;
    }

    // Filter aktiv olanda hər istifadəçi üzrə yalnız ən son gün (data artıq ən yenisindən sıralanıb)
    get displayedActivity() {
        let rows = this.state.activity;
        // istifadəçi adına görə axtarış (client-side, ani)
        const q = (this.state.activitySearch || '').trim().toLowerCase();
        if (q) {
            rows = rows.filter((g) => (g.user_name || '').toLowerCase().includes(q));
        }
        if (!this.state.latestOnly) {
            return rows;
        }
        const seen = new Set();
        const result = [];
        for (const grp of rows) {
            if (!seen.has(grp.user_id)) {
                seen.add(grp.user_id);
                result.push(grp);
            }
        }
        return result;
    }

    // ── Notes & Comments filtrləri ──────────────────────────────────────────

    toggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    setFilter(key, value) {
        if (key === 'student_id' || key === 'teacher_id' || key === 'group_id') {
            this.state.filters[key] = value ? parseInt(value, 10) : false;
        } else {
            this.state.filters[key] = value;
        }
        this.loadComments();
    }

    // Custom widget-lərdən gələn dəyər artıq düzgün tipdədir (parse etmə)
    applyFilter(key, value) {
        this.state.filters[key] = value;
        this.loadComments();
    }

    // Çoxseçimli filtr: dəyəri massivə əlavə et / çıxar
    toggleFilter(key, value) {
        const arr = this.state.filters[key] || [];
        const idx = arr.indexOf(value);
        if (idx === -1) {
            this.state.filters[key] = [...arr, value];
        } else {
            this.state.filters[key] = arr.filter((v) => v !== value);
        }
        this.loadComments();
    }

    // Çoxseçimli filtrin hamısını təmizlə
    clearFilter(key) {
        this.state.filters[key] = [];
        this.loadComments();
    }

    // ── Dropdown seçim siyahıları (custom FilterMultiSelect üçün) ────────────
    // Multi-select olduğu üçün "All …" sətri yoxdur — boş seçim = filtrsiz.
    get authorOptions() {
        return (this.state.filterOptions.authors || []).map((a) => ({ value: a, label: a }));
    }
    get teacherOptions() {
        return (this.state.filterOptions.teachers || []).map((t) => ({ value: t.id, label: t.name }));
    }
    get studentOptions() {
        return (this.state.filterOptions.students || []).map((s) => ({ value: s.id, label: s.name }));
    }
    get groupOptions() {
        return (this.state.filterOptions.groups || []).map((g) => ({ value: g.id, label: g.name }));
    }
    get sourceOptions() {
        return (this.state.filterOptions.sources || []).map((s) => ({ value: s, label: s }));
    }
    get dateModeOptions() {
        return [
            { value: 'all', label: 'All dates' },
            { value: 'year', label: 'This year' },
            { value: 'month', label: 'This month' },
            { value: 'week', label: 'This week' },
            { value: 'between', label: 'Between…' },
            { value: 'day', label: 'Specific day' },
        ];
    }

    clearFilters() {
        this.state.filters.text = '';
        this.state.filters.author = [];
        this.state.filters.student_id = [];
        this.state.filters.teacher_id = [];
        this.state.filters.group_id = [];
        this.state.filters.source = [];
        this.state.filters.date_mode = 'all';
        this.state.filters.date_from = '';
        this.state.filters.date_to = '';
        this.state.filters.date_one = '';
        this.loadComments();
    }

    // date_mode-a görə faktiki tarix aralığını (date_from/date_to) hesablayır
    _buildFilterPayload() {
        const f = this.state.filters;
        const pad = (n) => String(n).padStart(2, '0');
        const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        const today = new Date();
        let date_from = '';
        let date_to = '';
        if (f.date_mode === 'year') {
            date_from = `${today.getFullYear()}-01-01`;
            date_to = `${today.getFullYear()}-12-31`;
        } else if (f.date_mode === 'month') {
            const y = today.getFullYear();
            const m = today.getMonth();
            date_from = iso(new Date(y, m, 1));
            date_to = iso(new Date(y, m + 1, 0));
        } else if (f.date_mode === 'week') {
            const day = (today.getDay() + 6) % 7; // Bazar ertəsi = 0
            const mon = new Date(today);
            mon.setDate(today.getDate() - day);
            const sun = new Date(mon);
            sun.setDate(mon.getDate() + 6);
            date_from = iso(mon);
            date_to = iso(sun);
        } else if (f.date_mode === 'between') {
            date_from = f.date_from || '';
            date_to = f.date_to || '';
        } else if (f.date_mode === 'day') {
            date_from = f.date_one || '';
            date_to = f.date_one || '';
        }
        return {
            text: f.text,
            author: f.author,           // massiv
            student_id: f.student_id,   // massiv
            teacher_id: f.teacher_id,   // massiv
            group_id: f.group_id,       // massiv
            source: f.source,           // massiv
            date_from,
            date_to,
        };
    }

    async loadComments() {
        this.state.loadingComments = true;
        const res = await this.orm.call(
            "user.login.log",
            "get_dashboard_comments",
            [],
            { filters: this._buildFilterPayload(), limit: 200 }
        );
        this.state.comments = (res && res.comments) || [];
        if (res && res.options) {
            this.state.filterOptions = res.options;
        }
        this.state.loadingComments = false;
    }

    async loadActivity() {
        this.state.loadingActivity = true;
        this.state.activity = await this.orm.call(
            "user.login.log",
            "get_dashboard_activity",
            [],
            { limit: 100 }
        );
        this.state.loadingActivity = false;
    }

    async refresh() {
        await Promise.all([this.loadComments(), this.loadActivity()]);
    }

    clearActivity() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Clear Activity"),
            body: _t("Bütün istifadəçi aktivlik qeydləri silinsin? Bu əməliyyat geri qaytarıla bilməz."),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                await this.orm.call("user.login.log", "clear_activity_logs", []);
                await this.loadActivity();
            },
            cancel: () => {},
        });
    }

    openRecord(model, id) {
        if (!model || !id) {
            return;
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

registry.category("actions").add("staff_dashboard.Dashboard", StaffDashboard);
