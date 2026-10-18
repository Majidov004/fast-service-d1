/** @odoo-module **/
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Staff-dashboard filtr stilində (o_fsel) custom combobox.
 * Yazıb axtarırsan; uyğun seçim varsa siyahıdan seçirsən; yoxdursa altda
 * Odoo-vari **Create "<yazı>"** sətri görünür → klik = yarat və seç.
 * Props: options ([{id,name}]), displayName?, placeholder?, onChoose(opt), onCreate(name), onClear?
 */
export class EmployeeCombo extends Component {
    static template = "hr_employee_custom.EmployeeCombo";
    static props = {
        options: { type: Array },
        displayName: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        onChoose: Function,
        onCreate: Function,
        onClear: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({ open: false, search: "" });
        this.root = useRef("root");
        this.inputRef = useRef("input");
        this._onDocClick = (ev) => {
            if (this.state.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.close();
            }
        };
        onMounted(() => document.addEventListener("mousedown", this._onDocClick));
        onWillUnmount(() => document.removeEventListener("mousedown", this._onDocClick));
    }

    get displayLabel() {
        return this.props.displayName || this.props.placeholder || "Select…";
    }
    get isPlaceholder() {
        return !this.props.displayName;
    }
    get filtered() {
        const q = (this.state.search || "").trim().toLowerCase();
        const opts = this.props.options || [];
        if (!q) {
            return opts;
        }
        return opts.filter((o) => (o.name || "").toLowerCase().includes(q));
    }
    get exactExists() {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) {
            return true;
        }
        return (this.props.options || []).some((o) => (o.name || "").toLowerCase() === q);
    }
    get canCreate() {
        return !!this.state.search.trim() && !this.exactExists;
    }

    onSearch(ev) {
        this.state.search = ev.target.value;
    }

    toggle() {
        this.state.open = !this.state.open;
        if (this.state.open) {
            this.state.search = "";
            Promise.resolve().then(() => this.inputRef.el && this.inputRef.el.focus());
        }
    }
    close() {
        this.state.open = false;
    }
    choose(opt) {
        this.props.onChoose(opt);
        this.close();
    }
    create() {
        const name = this.state.search.trim();
        if (!name) {
            return;
        }
        this.props.onCreate(name);
        this.close();
    }
    clearValue() {
        if (this.props.onClear) {
            this.props.onClear();
        }
        this.close();
    }
    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            const q = this.state.search.trim().toLowerCase();
            const exact = (this.props.options || []).find(
                (o) => (o.name || "").toLowerCase() === q
            );
            if (exact) {
                this.choose(exact);
            } else if (q) {
                this.create();
            }
        } else if (ev.key === "Escape") {
            this.close();
        }
    }
}

/**
 * Universal OWL cədvəl widget-i — bir One2many xəttini kart/cədvəl şəklində
 * göstərir, sətir əlavə/sil və hər xananı yerindəcə redaktə edir.
 * Birbaşa ORM RPC ilə işləyir (contact_notes kimi) → dəyişiklik DƏRHAL yadda
 * saxlanır; standart "Save/Discard" tsiklindən kənardır.
 *
 * Konfiqurasiya alt-siniflərdə `config` getter-i ilə verilir:
 *   { model, parentField, fixed:{...}, columns:[{name,label,type:'char'|'m2o',model?}], addLabel }
 */
export class EmployeeTableBase extends Component {
    static template = "hr_employee_custom.EmployeeTable";
    static components = { EmployeeCombo };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ rows: [] });
        this.selectOptions = {};

        onWillStart(async () => {
            // lookup (m2o / combo) sütunlar üçün seçim siyahılarını yüklə
            for (const col of this.config.columns) {
                if (col.type === "m2o" || col.type === "combo") {
                    this.selectOptions[col.name] = await this.orm.searchRead(
                        col.model, [], ["name"]
                    );
                }
            }
        });

        // resId dəyişəndə (yeni qeyd ilk dəfə saxlananda da) sətirləri yenidən yüklə
        useEffect(
            () => {
                this.loadRows();
            },
            () => [this.props.record.resId]
        );
    }

    get resId() {
        return this.props.record.resId;
    }

    get config() {
        // alt-siniflər override edir
        return { model: "", parentField: "employee_id", fixed: {}, columns: [], addLabel: "Add" };
    }

    async loadRows() {
        if (!this.resId) {
            this.state.rows = [];
            return;
        }
        const cfg = this.config;
        const parent = cfg.parentField || "employee_id";
        const domain = [[parent, "=", this.resId]];
        for (const [k, v] of Object.entries(cfg.fixed || {})) {
            domain.push([k, "=", v]);
        }
        const fieldNames = cfg.columns.map((c) => c.name);
        this.state.rows = await this.orm.searchRead(cfg.model, domain, fieldNames);
    }

    async addRow() {
        if (!this.resId) {
            return;
        }
        const cfg = this.config;
        const vals = { [cfg.parentField || "employee_id"]: this.resId, ...(cfg.fixed || {}) };
        await this.orm.create(cfg.model, [vals]);
        await this.loadRows();
    }

    async deleteRow(row) {
        await this.orm.unlink(this.config.model, [row.id]);
        await this.loadRows();
    }

    cellText(row, col) {
        const v = row[col.name];
        // m2o / combo dəyəri [id, name] formatında gəlir → adı göstər
        if (Array.isArray(v)) {
            return v[1] || "";
        }
        return v || "";
    }

    isSelected(row, col, optId) {
        const v = row[col.name];
        return Array.isArray(v) && v[0] === optId;
    }

    async onCell(row, col, value) {
        await this.orm.write(this.config.model, [row.id], { [col.name]: value });
        row[col.name] = value;
    }

    // Combo — mövcud seçim seçildi
    async onComboChoose(row, col, opt) {
        await this.orm.write(this.config.model, [row.id], { [col.name]: opt.id });
        row[col.name] = [opt.id, opt.name];
    }

    // Combo — yeni dəyər: lookup-da DƏRHAL yarat və seç
    async onComboCreate(row, col, name) {
        const [newId] = await this.orm.create(col.model, [{ name }]);
        this.selectOptions[col.name] = await this.orm.searchRead(col.model, [], ["name"]);
        await this.orm.write(this.config.model, [row.id], { [col.name]: newId });
        row[col.name] = [newId, name];
    }

    // Combo — təmizlə
    async onComboClear(row, col) {
        await this.orm.write(this.config.model, [row.id], { [col.name]: false });
        row[col.name] = false;
    }
}

// ── Alt-siniflər (hər biri öz sütun konfiqurasiyası) ─────────────────────────

export class EmployeeLanguageTable extends EmployeeTableBase {
    get config() {
        return {
            model: "hr.employee.language",
            parentField: "employee_id",
            fixed: {},
            columns: [
                { name: "language_id", label: "Language", type: "combo", model: "hr.language" },
                { name: "level_id", label: "Level", type: "combo", model: "hr.language.level" },
            ],
            addLabel: "Add language",
        };
    }
}

export class EmployeeWorkTable extends EmployeeTableBase {
    get config() {
        return {
            model: "hr.employee.experience",
            parentField: "employee_id",
            fixed: { kind: "work" },
            columns: [
                { name: "place_id", label: "Place", type: "combo", model: "trail.lesson.config.company" },
                { name: "role_id", label: "Role / What", type: "combo", model: "trail.lesson.config.position" },
                { name: "duration", label: "Duration", type: "char" },
            ],
            addLabel: "Add work experience",
        };
    }
}

export class EmployeeVolunteerTable extends EmployeeTableBase {
    get config() {
        return {
            model: "hr.employee.experience",
            parentField: "employee_id",
            fixed: { kind: "volunteer" },
            columns: [
                { name: "place_id", label: "Place", type: "combo", model: "trail.lesson.config.company" },
                { name: "role_id", label: "Role / What", type: "combo", model: "trail.lesson.config.position" },
                { name: "duration", label: "Duration", type: "char" },
            ],
            addLabel: "Add volunteer experience",
        };
    }
}

export class EmployeeEnglishTable extends EmployeeTableBase {
    get config() {
        return {
            model: "hr.employee.experience",
            parentField: "employee_id",
            fixed: { kind: "english_teaching" },
            columns: [
                { name: "place_id", label: "Place", type: "combo", model: "trail.lesson.config.company" },
                { name: "role_id", label: "What you did", type: "combo", model: "trail.lesson.config.position" },
                { name: "duration", label: "Duration", type: "char" },
            ],
            addLabel: "Add entry",
        };
    }
}

export class EmployeeCertificateTable extends EmployeeTableBase {
    get config() {
        return {
            model: "hr.employee.certificate",
            parentField: "employee_id",
            fixed: {},
            columns: [
                { name: "certificate_id", label: "Certificate", type: "combo", model: "hr.certificate.type" },
                { name: "issued_by_id", label: "Issued By", type: "combo", model: "trail.lesson.config.school" },
                { name: "year", label: "Year", type: "char" },
            ],
            addLabel: "Add certificate",
        };
    }
}

const fields = registry.category("fields");
fields.add("employee_language_table", { component: EmployeeLanguageTable, supportedTypes: ["one2many"] });
fields.add("employee_work_table", { component: EmployeeWorkTable, supportedTypes: ["one2many"] });
fields.add("employee_volunteer_table", { component: EmployeeVolunteerTable, supportedTypes: ["one2many"] });
fields.add("employee_english_table", { component: EmployeeEnglishTable, supportedTypes: ["one2many"] });
fields.add("employee_certificate_table", { component: EmployeeCertificateTable, supportedTypes: ["one2many"] });
