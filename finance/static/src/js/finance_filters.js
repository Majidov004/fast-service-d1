/** @odoo-module **/
import { Component, xml, useState, useRef, onMounted, onWillUnmount, useEffect } from "@odoo/owl";

const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];

/**
 * Styled custom dropdown (replaces the native <select>).
 * Props: label?, icon?, value?, options ([{value, label}]), placeholder?, onSelect
 * Same look & feel as the Staff Dashboard filters.
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
          <input t-if="props.searchable" type="text" class="o_fsel_search" t-ref="search"
                 placeholder="Search..." t-att-value="state.query"
                 t-on-click.stop="" t-on-input="(ev) => this.onSearch(ev)"/>
          <t t-foreach="filteredOptions" t-as="opt" t-key="opt_index">
            <div t-attf-class="o_fsel_opt {{ opt.value === props.value ? 'o_active' : '' }}"
                 t-on-click="() => this.select(opt.value)">
              <span class="o_fsel_opt_label"><t t-esc="opt.label"/></span>
              <i t-if="opt.value === props.value" class="fa fa-check o_fsel_opt_check"/>
            </div>
          </t>
          <div t-if="filteredOptions.length === 0" class="o_fsel_opt o_fsel_empty">No results</div>
        </div>
      </div>`;

    static props = ["label?", "icon?", "value?", "options", "placeholder?", "searchable?", "onSelect"];

    setup() {
        this.state = useState({ open: false, query: "" });
        this.root = useRef("root");
        this.searchRef = useRef("search");
        this._onDocClick = (ev) => {
            if (this.state.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("mousedown", this._onDocClick));
        onWillUnmount(() => document.removeEventListener("mousedown", this._onDocClick));
        // focus the search box when the menu opens
        useEffect(
            () => {
                if (this.state.open && this.props.searchable && this.searchRef.el) {
                    this.searchRef.el.focus();
                }
            },
            () => [this.state.open]
        );
    }

    get _selected() {
        return this.props.options.find((o) => o.value === this.props.value);
    }
    get filteredOptions() {
        if (!this.props.searchable || !this.state.query) {
            return this.props.options;
        }
        const q = this.state.query.toLowerCase();
        return this.props.options.filter((o) => (o.label || "").toLowerCase().includes(q));
    }
    onSearch(ev) {
        this.state.query = ev.target.value;
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
        this.state.query = "";
    }
    select(value) {
        this.props.onSelect(value);
        this.state.open = false;
        this.state.query = "";
    }
}

/**
 * Styled custom date picker (mini calendar, replaces native <input type="date">).
 * Props: label?, value? ('YYYY-MM-DD' or ''), onSelect
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
        return this.props.value || "dd-mm-yyyy";
    }

    get monthLabel() {
        return `${MONTHS[this.state.m]} ${this.state.y}`;
    }

    get cells() {
        const y = this.state.y;
        const m = this.state.m;
        const first = new Date(y, m, 1);
        const offset = (first.getDay() + 6) % 7; // Monday = 0
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
