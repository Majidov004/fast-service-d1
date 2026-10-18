/** @odoo-module **/
import { Component, xml, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];

/**
 * Gözəl özəl dropdown — native <select> əvəzinə.
 * Props: label?, icon?, value?, options (array of {value, label}), placeholder?, onSelect
 */
export class FilterSelect extends Component {
    static template = xml`
      <div class="o_fsel" t-ref="root">
        <label t-if="props.label" class="o_filter_label">
          <i t-if="props.icon" t-attf-class="fa {{ props.icon }}"/> <t t-esc="props.label"/>
        </label>
        <button type="button" t-attf-class="o_fsel_trigger {{ state.open ? 'o_open' : '' }}"
                t-on-click="toggle">
          <span t-attf-class="o_fsel_value {{ isPlaceholder ? 'o_fsel_placeholder' : '' }}">
            <t t-esc="currentLabel"/>
          </span>
          <i class="fa fa-angle-down o_fsel_caret"/>
        </button>
        <div t-if="state.open" class="o_fsel_menu">
          <t t-foreach="props.options" t-as="opt" t-key="opt_index">
            <div t-attf-class="o_fsel_opt {{ opt.value === props.value ? 'o_active' : '' }}"
                 t-on-click="() => this.select(opt.value)">
              <span class="o_fsel_opt_label"><t t-esc="opt.label"/></span>
              <i t-if="opt.value === props.value" class="fa fa-check o_fsel_opt_check"/>
            </div>
          </t>
        </div>
      </div>`;

    static props = ["label?", "icon?", "value?", "options", "placeholder?", "onSelect"];

    setup() {
        this.state = useState({ open: false });
        this.root = useRef("root");
        this._onDocClick = (ev) => {
            if (this.state.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("mousedown", this._onDocClick));
        onWillUnmount(() => document.removeEventListener("mousedown", this._onDocClick));
    }

    get _selected() {
        return this.props.options.find((o) => o.value === this.props.value);
    }
    get isPlaceholder() {
        const v = this.props.value;
        return v === false || v === "" || v === undefined;
    }
    get currentLabel() {
        const opt = this._selected;
        return opt ? opt.label : (this.props.placeholder || "");
    }

    toggle() {
        this.state.open = !this.state.open;
    }
    select(value) {
        this.props.onSelect(value);
        this.state.open = false;
    }
}

/**
 * Çoxseçimli özəl dropdown — eyni filtr daxilində birdən çox dəyər seçməyə imkan verir
 * (məs. iki müəllim). Menyu seçimdən sonra AÇIQ qalır.
 * Props: label?, icon?, values? (seçilmiş dəyərlərin massivi), options ({value,label}),
 *        placeholder?, onToggle (fn(value) — əlavə/çıxar), onClear? (fn — hamısını sil)
 */
export class FilterMultiSelect extends Component {
    static template = xml`
      <div class="o_fsel o_fmulti" t-ref="root">
        <label t-if="props.label" class="o_filter_label">
          <i t-if="props.icon" t-attf-class="fa {{ props.icon }}"/> <t t-esc="props.label"/>
        </label>
        <button type="button" t-attf-class="o_fsel_trigger {{ state.open ? 'o_open' : '' }}"
                t-on-click="toggle">
          <span t-attf-class="o_fsel_value {{ count === 0 ? 'o_fsel_placeholder' : '' }}">
            <t t-esc="currentLabel"/>
          </span>
          <span t-if="count > 0" class="o_fmulti_count"><t t-esc="count"/></span>
          <i class="fa fa-angle-down o_fsel_caret"/>
        </button>
        <div t-if="state.open" class="o_fsel_menu">
          <div t-if="count > 0" class="o_fmulti_clear" t-on-click="clearAll">
            <i class="fa fa-times me-1"/> Clear selection
          </div>
          <t t-foreach="props.options" t-as="opt" t-key="opt_index">
            <div t-attf-class="o_fsel_opt {{ isSelected(opt.value) ? 'o_active' : '' }}"
                 t-on-click="() => this.toggleOpt(opt.value)">
              <span class="o_fsel_opt_label"><t t-esc="opt.label"/></span>
              <i t-if="isSelected(opt.value)" class="fa fa-check o_fsel_opt_check"/>
            </div>
          </t>
        </div>
      </div>`;

    static props = ["label?", "icon?", "values?", "options", "placeholder?", "onToggle", "onClear?"];

    setup() {
        this.state = useState({ open: false });
        this.root = useRef("root");
        this._onDocClick = (ev) => {
            if (this.state.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("mousedown", this._onDocClick));
        onWillUnmount(() => document.removeEventListener("mousedown", this._onDocClick));
    }

    get _values() {
        return this.props.values || [];
    }
    get count() {
        return this._values.length;
    }
    get currentLabel() {
        const vals = this._values;
        if (!vals.length) {
            return this.props.placeholder || "";
        }
        if (vals.length === 1) {
            const opt = this.props.options.find((o) => o.value === vals[0]);
            return opt ? opt.label : "1 selected";
        }
        return `${vals.length} selected`;
    }
    isSelected(value) {
        return this._values.includes(value);
    }

    toggle() {
        this.state.open = !this.state.open;
    }
    toggleOpt(value) {
        // menyu açıq qalır ki, ardıcıl bir neçə dəyər seçilə bilsin
        this.props.onToggle(value);
    }
    clearAll() {
        if (this.props.onClear) {
            this.props.onClear();
        }
        this.state.open = false;
    }
}

/**
 * Gözəl özəl tarix seçici (mini təqvim) — native <input type="date"> əvəzinə.
 * Props: label?, value? ('YYYY-MM-DD' və ya ''), onSelect
 */
export class FilterDate extends Component {
    static template = xml`
      <div class="o_fsel o_fdate" t-ref="root">
        <label t-if="props.label" class="o_filter_label"><t t-esc="props.label"/></label>
        <button type="button" t-attf-class="o_fsel_trigger {{ state.open ? 'o_open' : '' }}"
                t-on-click="toggle">
          <span t-attf-class="o_fsel_value {{ props.value ? '' : 'o_fsel_placeholder' }}">
            <t t-esc="displayValue"/>
          </span>
          <i class="fa fa-calendar o_fsel_caret"/>
        </button>
        <div t-if="state.open" class="o_fcal">
          <div class="o_fcal_head">
            <button type="button" class="o_fcal_nav" t-on-click="prevMonth"><i class="fa fa-angle-left"/></button>
            <span class="o_fcal_title"><t t-esc="monthLabel"/></span>
            <button type="button" class="o_fcal_nav" t-on-click="nextMonth"><i class="fa fa-angle-right"/></button>
          </div>
          <div class="o_fcal_dow">
            <span t-foreach="dow" t-as="d" t-key="d_index"><t t-esc="d"/></span>
          </div>
          <div class="o_fcal_grid">
            <t t-foreach="cells" t-as="cell" t-key="cell_index">
              <span t-if="!cell" class="o_fcal_cell o_empty"/>
              <span t-else=""
                    t-attf-class="o_fcal_cell {{ cell.iso === props.value ? 'o_sel' : '' }} {{ cell.today ? 'o_today' : '' }}"
                    t-on-click="() => this.pick(cell.iso)">
                <t t-esc="cell.day"/>
              </span>
            </t>
          </div>
          <div class="o_fcal_foot">
            <button type="button" class="o_fcal_link o_clear" t-on-click="clear">Clear</button>
            <button type="button" class="o_fcal_link" t-on-click="goToday">Today</button>
          </div>
        </div>
      </div>`;

    static props = ["label?", "value?", "onSelect"];

    setup() {
        this.state = useState({ open: false, y: 2000, m: 0 });
        this.root = useRef("root");
        this.dow = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
        this._syncView();
        this._onDocClick = (ev) => {
            if (this.state.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("mousedown", this._onDocClick));
        onWillUnmount(() => document.removeEventListener("mousedown", this._onDocClick));
    }

    _syncView() {
        if (this.props.value) {
            const [y, m] = this.props.value.split("-").map(Number);
            this.state.y = y;
            this.state.m = m - 1;
        } else {
            const t = new Date();
            this.state.y = t.getFullYear();
            this.state.m = t.getMonth();
        }
    }

    _pad(n) {
        return String(n).padStart(2, "0");
    }
    _todayIso() {
        const t = new Date();
        return `${t.getFullYear()}-${this._pad(t.getMonth() + 1)}-${this._pad(t.getDate())}`;
    }

    get displayValue() {
        return this.props.value || "gg.aa.yyyy";
    }

    get monthLabel() {
        return `${MONTHS[this.state.m]} ${this.state.y}`;
    }

    get cells() {
        const y = this.state.y;
        const m = this.state.m;
        const first = new Date(y, m, 1);
        const offset = (first.getDay() + 6) % 7; // Bazar ertəsi = 0
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const todayIso = this._todayIso();
        const cells = [];
        for (let i = 0; i < offset; i++) {
            cells.push(null);
        }
        for (let d = 1; d <= daysInMonth; d++) {
            const iso = `${y}-${this._pad(m + 1)}-${this._pad(d)}`;
            cells.push({ day: d, iso, today: iso === todayIso });
        }
        return cells;
    }

    toggle() {
        if (!this.state.open) {
            this._syncView();
        }
        this.state.open = !this.state.open;
    }
    prevMonth() {
        if (this.state.m === 0) {
            this.state.m = 11;
            this.state.y -= 1;
        } else {
            this.state.m -= 1;
        }
    }
    nextMonth() {
        if (this.state.m === 11) {
            this.state.m = 0;
            this.state.y += 1;
        } else {
            this.state.m += 1;
        }
    }
    pick(iso) {
        this.props.onSelect(iso);
        this.state.open = false;
    }
    goToday() {
        this.pick(this._todayIso());
    }
    clear() {
        this.props.onSelect("");
        this.state.open = false;
    }
}
