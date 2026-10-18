# staff_dashboard — Module Map

**Odoo 18 | Application | Lesson comment feed + user login/activity tracking dashboard**

Depends: `base`, `hr`, `lesson_record`

---

## File Tree

```
staff_dashboard/
├── __manifest__.py                  → Module metadata, dependencies, assets
├── __init__.py                      → Imports models + controllers packages
├── controllers/
│   ├── __init__.py                  → Imports main
│   └── main.py                      → Extends /web/session/logout → closes the active session on logout
├── models/
│   ├── __init__.py                  → Imports user_login_log
│   └── user_login_log.py            → Core log model: stores sessions (keyed by session id), durations, dashboard data
├── views/
│   ├── dashboard_action.xml         → ir.actions.client pointing to OWL component tag
│   └── menu.xml                     → Root menu item + Dashboard child menu item
├── security/
│   └── ir.model.access.csv          → Access rules for user.login.log
└── static/
    └── src/
        ├── css/
        │   └── dashboard.css        → All dashboard styles (panels, cards, table, badges)
        ├── js/
        │   ├── dashboard.js         → OWL StaffDashboard component (main dashboard)
        │   ├── filter_widgets.js    → Custom OWL FilterSelect + FilterDate (styled dropdown & calendar)
        │   └── activity_service.js  → Background OWL service: heartbeat + URL navigation tracking
        └── xml/
            └── dashboard.xml        → QWeb/OWL template for the dashboard UI
```

---

## Models

### user.login.log (`models/user_login_log.py`)

**Technical name:** `user.login.log`
**Description:** User Login Log
**Default order:** `login_time desc`

#### Fields

| Field            | Type         | Notes                                                                 |
|------------------|--------------|-----------------------------------------------------------------------|
| `user_id`        | Many2one     | → `res.users`; required; ondelete=cascade                            |
| `login_time`     | Datetime     | Required; defaults to `fields.Datetime.now`                          |
| `last_activity`  | Datetime     | Defaults to `fields.Datetime.now`; updated by heartbeat              |
| `session_end`    | Datetime     | Set on logout (via controller `close_session`); marks the session as closed. A closed session is never re-used by heartbeat |
| `session_token`  | Char (indexed) | **Per-page-load client token** sent by the frontend (falls back to the HTTP sid if absent). This is the key that uniquely identifies a session. The frontend generates a fresh in-memory token on every full page load (link entry, login redirect, tab reopen, F5), so each entry becomes its own row; heartbeats of the same loaded page share one row |
| `current_module` | Char         | URL path of last visited module; updated by heartbeat                |
| `duration_display` | Char (computed) | `_compute_duration`; formatted as `Xh Ym` or `Ym`; depends on `login_time`, `last_activity` |

#### Methods

**`_compute_duration(self)`**
- Computes `duration_display` for each record.
- Calculates `delta = last_activity - login_time`, converts to total minutes, formats as `"{h}h {m}m"` if hours > 0, else `"{m}m"`. Returns `'—'` if either datetime is missing.

**`_current_sid(self)`** — `@api.model`
- Returns `odoo.http.request.session.sid` (the HTTP session id). Wrapped in try/except → returns `False` outside an HTTP context (cron/tests). Used only as a fallback key when the frontend doesn't supply a `client_token`.

**`update_heartbeat(self, module_path='', client_token=False)`** — `@api.model`
- Called by the frontend JS service every 2 minutes and on URL change. All ORM ops use `sudo()`.
- Computes the session key: `key = client_token or _current_sid()`.
- **If `key` exists:** finds the OPEN row (`session_end` empty) with `user_id` + `session_token == key`. Found → updates `last_activity` (and `current_module`). Not found → **creates a new row** stamped with `key`. This is the core: same loaded page → same token → same row (no duplicates); a new page load / link entry → new token → new row (new session shows up). **Why `client_token` instead of just the sid:** with link/cookie auto-login the HTTP sid does NOT change between entries, so sid alone merged everything into one session. The per-page-load token solves exactly that.
- **Fallback if `key` is empty:** reuses the user's latest open session unless its `last_activity` is ≥ 15 minutes stale, otherwise creates a new row.

**`close_session(self, uid=None)`** — `@api.model`
- Called by the logout controller. Closes the user's latest OPEN row by setting `session_end = last_activity = now`. Improves duration accuracy. (The logout redirect also forces a fresh page load → new token → the next entry is a new session anyway.)

**`clear_activity_logs(self)`** — `@api.model`
- Backs the dashboard **Clear** button. Raises `AccessError` unless the caller is in `base.group_system` (admin only). Then deletes ALL `user.login.log` records via `sudo().search([]).unlink()`. Irreversible. The current user's session is recreated on the next heartbeat (within ~30s–2min).

**`_calc_duration_mins(self, log, now, is_latest_for_user=False)`**
- Private helper used by `get_dashboard_activity`.
- If `is_latest_for_user=True` and `last_activity` is within 15 minutes of `now`, treats the session as still active: computes `now - login_time`.
- Otherwise uses `(last_activity or login_time) - login_time`.
- Returns duration in whole minutes (minimum 0).

**`_fmt(total_mins)`** — `@staticmethod`
- Formats a total-minutes integer into `"Xh Ym"` or `"Ym"` string.

**`get_dashboard_activity(self, limit=200)`** — `@api.model`
- Fetches up to `limit` log records ordered by `login_time desc`.
- Determines the **most recent log id per user** (`latest_per_user` dict) — only that session can be considered "active".
- Groups logs by `(user_id, local_date)` key (`"{uid}_{YYYY-MM-DD}"`). UTC login times are converted to context-local timezone via `fields.Datetime.context_timestamp`.
- For each log in a group, calls `_calc_duration_mins` and accumulates `total_mins`.
- Returns a list of group dicts in order of appearance (most recent first), each containing:
  - `key` — group key string
  - `user_id` — user id (used by the client-side "Latest only" filter to dedupe per user)
  - `user_name` — user display name
  - `date` — formatted date string (`DD Mon YYYY`)
  - `total_duration` — formatted total duration string
  - `sessions` — list of session dicts: `{login_time (HH:MM), duration, active (bool)}`

**`_fmt_comment_date(self, rec, written_at)`**
- Helper. Converts a datetime (or date) to the user's local timezone and returns `(display_str, sort_str)` both as `'%Y-%m-%d %H:%M'` (or `str()` for date-only). Used by the unified feed.

**`_collect_all_comments(self, cap=1000)`**
- Gathers ALL note/comment rows from the four sources into one unified list (no filtering). Each row carries display fields (`type`, `type_label`, `icon`, `author_name`, `teacher_name`/`student_name`/`contact_name`, `title`, `comment`, `res_model`/`res_id`, `date`/`date_sort`) **plus filter fields**: `source` (module name — "Lesson Record" / "Contact Notes" / "Trail Lesson"), `student_id` (the person the note is about — line student / partner / trial student), `group_id`+`group_name` (lesson's training group; empty for contact/trial), and `date_key` (`YYYY-MM-DD`, local).
  Filter fields also include **`teacher_id`** (lesson/trial teacher; empty for contact).
  1. **`type='student'`**, "Lesson - Comment for Student" — `lesson.student.line.comment` → `lesson.record`; `student_id`+`teacher_id`+`group_id` set.
  2. **`type='teacher'`**, "Lesson - Comment for Lesson" — `lesson.record.teacher_comment` → `lesson.record`; `teacher_id`+`group_id` set, no `student_id`.
  3. **`type='contact'`**, "Student Note" — `contact.note.text` (module `contact_notes`) → `res.partner`; `student_id` = partner, `student_name` = partner name, `title=''`, no teacher/group. Guarded by `if 'contact.note' in self.env`.
  4. **`type='trial'`**, "Trial Lesson" — `trail.lesson.notes` (Html→`html2plaintext`) + `complete_notes` combined (module `trail_lesson`) → `trail.lesson`; `student_id`+`teacher_id` set; read with **`sudo()`** (0 ACL rows). Guarded by `if 'trail.lesson' in self.env`.
- Sources 3 & 4 are optional (guarded by `'<model>' in self.env`) — not hard manifest dependencies.

**`get_dashboard_comments(self, filters=None, limit=200)`** — `@api.model`
- The method the dashboard calls. Returns **`{'comments': [...], 'options': {...}}`**.
- Calls `_collect_all_comments()`, then:
  - Builds **`options`** (for the filter dropdowns) from the FULL set, independent of the active filters: `authors` (distinct names), `students` (`[{id,name}]`), `teachers` (`[{id,name}]`), `groups` (`[{id,name}]`), `sources` (distinct module names).
  - Applies the `filters` dict in Python: `text` (case-insensitive substring in comment); `author`, `student_id`, `teacher_id`, `group_id`, `source` are **multi-value** — each accepts a list and a row is kept when its value is `in` the selected list (OR within a filter, AND across filters); empty/omitted = no filter. A helper `_aslist()` wraps a bare scalar into a list, so old single-value callers still work. Plus a date range `date_from`/`date_to` (inclusive, compared against `date_key`).
  - Sorts by `date_sort` desc, truncates to `limit`.
- The frontend computes `date_from`/`date_to` from its date-mode preset (year/month/week/between/day) and sends them — the backend only sees a plain range.

> **Note:** There is intentionally **no `res.users._update_last_login` override**. An earlier version created a row at login time, but Odoo rotates the session id during authentication, so a row created there carried the OLD sid while the first heartbeat used the NEW sid → duplicate rows. Session rows are now created exclusively by `update_heartbeat` (keyed by the post-login sid). The first heartbeat fires immediately on page load, so the login time recorded is within ~1s of the real login.

---

## Controllers (`controllers/main.py`)

### `StaffDashboardSession(Session)`

Extends Odoo's standard web session controller (`odoo.addons.web.controllers.session.Session`).

**`logout(self, *args, **kw)`** — `@http.route()` (inherits the parent `/web/session/logout` route config)
- Reads `request.session.uid` BEFORE the session is destroyed.
- Calls `user.login.log.sudo().close_session(uid)` to stamp `session_end` on the active session.
- Wrapped in try/except so logout is never blocked by a logging error.
- Then calls `super().logout(*args, **kw)`.

This is what makes a logout → re-login pair show as **two separate sessions** even when the re-login is an automatic cookie/link login within 15 minutes (which would otherwise be merged by `update_heartbeat`).

---

## Frontend / OWL (`static/`)

### OWL Service: `activity_service.js`

Registered in the `services` registry as `"activity_tracker"`.
Depends on the `orm` service.

**Behavior on `start`:**
1. Records the current `window.location.pathname` as `currentPath`.
2. **Generates a unique in-memory `clientToken`** (```${Date.now().toString(36)}-${Math.random().toString(36).slice(2,10)}```). Because it lives in a local variable, it is regenerated on every full page load (link entry, login redirect, tab reopen, F5) but stays constant across SPA navigation within the same loaded page. This token is what makes each entry a distinct session.
3. Calls `update_heartbeat(module_path, client_token=clientToken)` immediately (first heartbeat on page load).
4. `setInterval` every **2 minutes** → heartbeat with current pathname + the same `clientToken`.
5. `setInterval` every **5 seconds** → if `window.location.pathname` changed, update `currentPath` and send an immediate heartbeat.

Errors from RPC calls are silently swallowed (`catch (_) {}`).

---

### Custom Filter Widgets: `filter_widgets.js`

Two small reusable OWL components (inline `xml` templates) used by the Notes & Comments filter bar, built to fully control the look of the popups (native `<select>` option lists and `<input type=date>` calendars cannot be styled). **Must be listed before `dashboard.js` in the manifest assets.**

**`FilterSelect`** — styled single-select dropdown replacing native `<select>`.
- Props: `label?`, `icon?`, `value?`, `options` (`[{value,label}]`), `placeholder?`, `onSelect` (fn).
- Renders a labeled trigger button + an absolutely-positioned styled menu (rounded, shadow, hover highlight, check mark on the active option, scrollable). Closes on outside click (document `mousedown` listener via a `t-ref="root"`). Emits the chosen option's raw `value` (int / string / `false`) to `onSelect`. **Still used only for the single-choice `Date` mode selector.**

**`FilterMultiSelect`** — styled **multi-select** dropdown (lets you pick several values in one filter, e.g. two teachers — OR within the filter).
- Props: `label?`, `icon?`, `values?` (array of selected values), `options` (`[{value,label}]`), `placeholder?`, `onToggle` (fn(value) — add/remove), `onClear?` (fn — wipe the whole filter).
- Trigger shows the single label when one is selected, else `"N selected"`, plus a small purple count badge (`.o_fmulti_count`). The menu **stays open** after a click so multiple options can be picked in a row; selected options show a check mark; a top `Clear selection` row (`.o_fmulti_clear`) appears when ≥1 is chosen. Closes on outside click.
- Used for the **Author / Teacher / Student / Group / Module** filters.

**`FilterDate`** — styled mini calendar replacing native `<input type="date">`.
- Props: `label?`, `value?` (`'YYYY-MM-DD'` or `''`), `onSelect` (fn).
- Trigger button + popup month grid (Mon-first), prev/next month nav, today highlight, selected highlight, **Clear** / **Today** footer links. Emits `'YYYY-MM-DD'` (or `''` for clear). Closes on outside click.
- Uses `new Date()` for "today" (allowed — browser JS, not a workflow script).

Styling for both lives in `dashboard.css` under the `.o_fsel*` (select) and `.o_fcal*` (calendar) rules.

---

### OWL Component: `dashboard.js`

**Class:** `StaffDashboard`
**Template:** `staff_dashboard.Dashboard`
**Registered in:** `actions` registry as `"staff_dashboard.Dashboard"`

#### State

| Property          | Type    | Purpose                                             |
|-------------------|---------|-----------------------------------------------------|
| `comments`        | Array   | Comment objects from `get_dashboard_comments` (`.comments`) |
| `activity`        | Array   | Activity group objects from `get_dashboard_activity`        |
| `loadingComments` | Boolean | Shows spinner while comments are loading            |
| `loadingActivity` | Boolean | Shows spinner while activity is loading             |
| `expanded`        | Object  | Maps group `key → boolean` for expand/collapse state |
| `latestOnly`      | Boolean | Activity filter. **Default `true`** → show only each user's most recent day. Toggled by the "Latest only" button |
| `showFilters`     | Boolean | Whether the Notes & Comments filter bar is open (Filter button) |
| `activitySearch`  | String  | User Activity panel — free-text search on the user name (client-side, instant) |
| `filters`         | Object  | Active comment filters. `text` (string) + `date_mode`/`date_from`/`date_to`/`date_one` (single) + **multi-value arrays**: `author`, `student_id`, `teacher_id`, `group_id`, `source` (each holds the list of selected values; empty array = no filter) |
| `filterOptions`   | Object  | Dropdown options from the backend: `authors[]`, `students[{id,name}]`, `teachers[{id,name}]`, `groups[{id,name}]`, `sources[]` |

Services used: `orm`, `action`, `dialog`.

#### Lifecycle

- `onWillStart`: calls `loadComments()` and `loadActivity()` in parallel via `Promise.all`. Data is loaded once on open and on demand via the Refresh button — there is **no auto-refresh timer**.

#### Methods

- **`loadComments()`** — calls `orm.call('user.login.log', 'get_dashboard_comments', [], {filters: this._buildFilterPayload(), limit: 200})`; stores `res.comments` → `state.comments` and `res.options` → `state.filterOptions`.
- **`toggleFilters()`** — opens/closes the filter bar (`state.showFilters`).
- **`setFilter(key, value)`** — updates one filter in `state.filters` and reloads. Used by the native Search text `<input>`.
- **`applyFilter(key, value)`** — sets a filter to an already-typed value (no parsing) and reloads. Used by the single-select `FilterSelect` (`date_mode`) and `FilterDate` widgets.
- **`toggleFilter(key, value)`** — multi-select: adds `value` to the `state.filters[key]` array if absent, removes it if present (reassigns a new array for reactivity), then reloads. Backs every `FilterMultiSelect` (`author`/`teacher_id`/`student_id`/`group_id`/`source`).
- **`clearFilter(key)`** — empties one multi-select array and reloads (the menu's `Clear selection` row).
- **`setActivitySearch(value)`** — sets `state.activitySearch` (User Activity name search). No RPC — filtering is client-side via `displayedActivity`.
- **option getters** — `authorOptions`, `teacherOptions`, `studentOptions`, `groupOptions`, `sourceOptions` map `state.filterOptions` into plain `[{value,label}]` arrays (**no "All …" prefix** — multi-select uses an empty array for "no filter") fed to `FilterMultiSelect`. `dateModeOptions` (with its preset entries) still feeds the single `FilterSelect`. `static components = { FilterSelect, FilterMultiSelect, FilterDate }`.
- **`clearFilters()`** — resets all filters to defaults and reloads.
- **`_buildFilterPayload()`** — converts `date_mode` into a concrete `date_from`/`date_to` range (year/month/week computed from today; between/day from the date inputs) and returns the payload sent to the backend.
- **`loadActivity()`** — same pattern for `get_dashboard_activity` → `state.activity`.
- **`refresh()`** — runs both loaders in parallel (Refresh button).
- **`clearActivity()`** — opens a `ConfirmationDialog` ("Clear Activity"); on confirm calls `clear_activity_logs` then reloads activity. Backs the red **Clear** button in the User Activity panel heading. Server-side enforces admin-only.
- **`toggleLatestOnly()`** — flips `state.latestOnly`. Backs the **Latest only** toggle button (highlighted `btn-secondary` when active, outline when off).
- **`get displayedActivity()`** — getter the activity table iterates over. First applies the `activitySearch` text filter (case-insensitive substring on `user_name`), then, when `latestOnly` is true, returns only the first group per `user_id` (data is ordered most-recent-first, so first = latest day); otherwise returns all matching groups. Purely client-side — no extra RPC. (The "No activity recorded." empty state is now keyed on `displayedActivity.length`, so a no-match search shows the message instead of an empty table.)
- **`toggleRow(key)`** — toggles `state.expanded[key]` to show/hide session detail rows.
- **`openRecord(model, id)`** — generic `action.doAction` opening the `model` form for `id` in the current tab (no-op if either missing). Replaces the old `openLesson`; each comment card now carries its own `res_model`/`res_id` (lesson.record / res.partner / trail.lesson).

---

### QWeb Template: `dashboard.xml`

Template name: `staff_dashboard.Dashboard`

**Structure:**

```
.o_staff_dashboard
  .o_dashboard_header
    h4 "Staff Dashboard"
    button [Refresh] → calls this.refresh()
  .o_dashboard_panels   (flex row, two equal panels)
    Panel 1: Notes & Comments
      heading: "Notes & Comments" + [Filter] toggle (→ toggleFilters)
      .o_comment_filters (t-if state.showFilters): Search (native styled input) + multi-select <FilterMultiSelect/> for Author/Teacher/Student/Group/Module + single <FilterSelect/> for Date-mode + custom <FilterDate/> for From/To/Day + [Clear]. All popups are custom OWL widgets (see filter_widgets.js) — slide-down animation, focus ring, hover styling.
      Loading spinner (t-if state.loadingComments)
      "No comments found." (t-elif comments.length === 0)
      .o_panel_scroll (t-else)
        for each comment c:
          .o_comment_card  (class is-{{c.type}}: student/teacher/contact/trial; clickable → openRecord(c.res_model, c.res_id))
            .o_card_row_top: author avatar (first letter) + author name | date
            .o_card_row_lesson: .o_type_badge (icon + type_label "Comment for Student"/"Comment for Lesson"/"Contact Note"/"Trial Lesson", colored per type) + .o_card_title (record reference; for contact notes this is the partner name)
            .o_card_meta: distinct pills — .o_meta_teacher ("Teacher: …", teal), .o_meta_student ("Student: …", purple), .o_meta_contact (contact name, blue) — each shown only if present
            .o_card_divider
            .o_comment_text: comment body
    Panel 2: User Activity
      heading: "User Activity" + .o_panel_actions [ [Latest only] toggle (→ toggleLatestOnly), red [Clear] (→ clearActivity) ]
      .o_activity_search: "Search user…" input (→ setActivitySearch, instant client-side name filter) + inline clear (×) when non-empty
      Loading spinner (t-if state.loadingActivity)
      "No activity recorded." (t-elif activity.length === 0)
      .o_panel_scroll (t-else)
        table.o_activity_table
          thead: User | Date | Total
          tbody:  (t-foreach="displayedActivity" — filtered when Latest only is on)
            for each group grp:
              .o_activity_group_row (clickable → toggleRow(grp.key))
                chevron icon (down if expanded, right if collapsed)
                avatar (first letter) + user_name | date | total_duration badge
              if state.expanded[grp.key]:
                for each session s:
                  .o_activity_detail_row
                    sign-in icon + login_time (HH:MM) | | duration badge
```

---

### Stylesheet: `dashboard.css`

All styles are scoped to the `.o_staff_dashboard` subtree. Key design tokens:
- Background: `#f5f6fa` (page), `#fff` (panels)
- Per-type accent colors (card left-border, avatar, type badge): student `#875a7b` (purple), teacher `#00a09d` (teal), contact `#3498db` (blue), trial `#e67e22` (orange)
- Type badge: `.o_type_badge.type-<type>` — small colored pill with icon + label in the card's second row
- Meta pills (`.o_card_meta`): `.o_meta_teacher` (teal), `.o_meta_student` (purple), `.o_meta_contact` (blue) — prominently mark who the teacher / student / contact is on each card
- Panels use `flex: 1` inside a flex row with `height: calc(100vh - 140px)`; each panel scrolls independently.
- Duration badge: `.o_duration_badge` (purple, rounded pill); smaller variant `.o_duration_sm` for detail rows.
- Comment cards have a 4px left border: purple for student (`is-student`), teal for teacher (`is-teacher`).

---

## Applicant Analytics (the "Analytics" tab)

Separate OWL client action `staff_dashboard.Analytics` (`static/src/js/analytics_dashboard.js`, template `static/src/xml/analytics_dashboard.xml`, styles `static/src/css/analytics_dashboard.css`). One RPC: `user.login.log.get_applicant_analytics()`. Read-only, current-month-focused, each metric compared to the previous month. Guarded: returns `{available: False}` if `res.partner.applicant_state` is missing (contact_customization not installed).

**`get_applicant_analytics()`** builds (all months are user-tz, converted to UTC for the SQL filter):
- `totals` — overall (not date-filtered) `people` (student or applicant), `students`, `applicants`.
- `stages` — the 11-stage funnel (`_ANALYTICS_STAGES`) counted by `create_date` in the current month grouped by current `applicant_state`, each with prev-month count + `_analytics_pct`.
- **`rates`** (A) — Conversion Rate (paid/registered), Loss Rate (no_answer+not_want+trial_no_contact, `good_up=False`), Active Pipeline (reg−paid−loss), New Registrations. Each via the `kpi()` helper → `{value, suffix, prev, change, tone}` where `tone` ∈ good/bad/flat drives the colour (handles "up is bad" for Loss Rate).
- **`sources`** (B) — this-month registrations grouped by `reference_source` + paid-per-source + conversion %, sorted desc. Labels from the field's selection. Empty if `reference_source` absent.
- **`trials`** (C) — `trail.lesson` (sudo, guarded by `'trail.lesson' in env`) within the month by `lesson_datetime`: total/planned/completed/missing + decision split (joining/thinking/not_joining for completed) + prev-month total.
- **`trend`** (E) — last 6 months, each `{label, registered, paid}`; the frontend draws CSS bars scaled to `trendMax` (max registered) via `barH(v)`.
- **`students`** (F) — total students, `new` (this-month new students as a `kpi()` card), `lead` breakdown (lead_state grouped over all students), `active_groups` (`training.group` state=in_progress, guarded).

Every card has a **hover tooltip** (native `title`) explaining what it means: funnel stages (`stage.help` from `_STAGE_HELP`), Key Rates + New Students (the `kpi()` helper's `tip` → `help`), and static titles on the top KPIs / Trial cards / Lead Sources / Trend / Students. Cards with a tooltip show a `cursor: help`.

Frontend renders: top 3 KPIs → Key Rates → Funnel → **Trial Lessons + Lead Sources side-by-side** (`.o_an_two`/`.o_an_half` two-column row, stacks on mobile) → Last 6 Months (bars) → Students. Sections self-hide when their data is empty/unavailable (a lone visible half still fills the width via `flex:1`). `kpi`/rate chips colour by `tone` (`o_an_pct_good/bad/flat`), funnel chips by direction (`o_an_pct_up/down`).

---

## Views

### `views/dashboard_action.xml`

Defines a single `ir.actions.client` record:

| Field  | Value                         |
|--------|-------------------------------|
| `id`   | `action_staff_dashboard`      |
| `name` | `Staff Dashboard`             |
| `tag`  | `staff_dashboard.Dashboard`   |

The `tag` value matches the key under which `StaffDashboard` is registered in the `actions` registry, causing Odoo to render the OWL component when this action is triggered.

### `views/menu.xml`

Two menu items:

| ID                        | Name             | Parent                      | Action                   | Sequence |
|---------------------------|------------------|-----------------------------|--------------------------|----------|
| `menu_staff_dashboard_root` | Staff Dashboard | — (top-level)               | —                        | 2        |
| `menu_staff_dashboard`      | Dashboard        | `menu_staff_dashboard_root` | `action_staff_dashboard` | 1        |

The root menu item references `static/description/icon.png` as its web icon (file not present in `static/src/`, expected at `static/description/icon.png`).

---

## Security

### `security/ir.model.access.csv`

| ID                              | Model               | Group               | Read | Write | Create | Unlink |
|---------------------------------|---------------------|---------------------|------|-------|--------|--------|
| `access_user_login_log_user`    | `user.login.log`    | `base.group_user`   | 1    | 0     | 1      | 0      |
| `access_user_login_log_admin`   | `user.login.log`    | `base.group_system` | 1    | 1     | 1      | 1      |

- Regular users can read and create log entries (required for heartbeat RPC creating records).
- Only system admins can write to or delete log entries.
- Regular users need `read` + `create` so the heartbeat RPC can look up and create their own session rows; `write`/`unlink` are admin-only (heartbeat/close/clear use `sudo()`).

---

## Important Notes

1. **Sessions are identified by a per-page-load client token (`session_token`).** This is the single most important design point. The frontend generates a fresh in-memory token on every full page load and sends it with each heartbeat. `update_heartbeat` looks up the OPEN row whose `session_token` equals that token: found → update it; not found → create a new row. Therefore: every fresh page load / link entry → new token → its own row → **new sessions always appear**; all heartbeats of one loaded page share one row → **no duplicate rows**. **Why not the HTTP sid?** With link/cookie auto-login the sid does NOT change between entries, so a sid key merged everything into one ever-growing session — which is exactly the bug observed. The client token changes per load, so it distinguishes entries without requiring a real logout. The sid remains only as a fallback key. There is intentionally **no `_update_last_login` override**. A genuine logout = a page reload anyway, so it also yields a new token/row.

2. **`session_token` and `session_end` are new fields — module upgrade required.** Adding them changes the DB schema. Run `odoo-bin -u staff_dashboard -d <db>` (a plain server restart is not enough) before testing, then hard-reload the browser (Ctrl+F5) so the new JS/CSS load.

3. **`lesson_record` dependency is mandatory.** `_collect_all_comments` directly queries `lesson.student.line` and `lesson.record`. If `lesson_record` is not installed, installation fails.

4. **`hr` dependency is declared but not used directly.** No `hr.*` model is referenced. Likely a forward/implicit dependency.

5. **All log writes use `sudo()`.** `update_heartbeat`, `close_session` and the logout controller all write with `sudo()` because regular users have `perm_write=0` / `perm_unlink=0` on `user.login.log` (they may only read and create).

6. **Session "active" detection window is 15 minutes (display only).** In `_calc_duration_mins`, a session counts as still active (duration = `now - login_time`) only if `last_activity` is within the last 15 minutes; otherwise duration = `last_activity - login_time`. This is purely for the dashboard's live duration display.

7. **Heartbeat interval: 2 minutes / URL check: 5 seconds.** `activity_service.js` fires a heartbeat every 2 minutes, plus whenever the URL pathname changes (checked every 5s). So `last_activity` on the active session is at most ~2 minutes stale.

8. **No auto-refresh.** The dashboard loads data on open and only re-fetches when the **Refresh** button is pressed. Switching OS windows does nothing — the browser tab stays put and the component does not poll.

15. **"Latest only" activity filter (default ON).** The User Activity panel shows, by default, only each user's most recent day (with its expandable session details). The **Latest only** toggle button switches between this and the full history. It is a client-side filter over already-fetched data (`displayedActivity` getter, deduped by `user_id`); turning it off shows every (user, day) group.

16. **"Notes & Comments" is a unified cross-module feed.** Rows are gathered by `_collect_all_comments()` from four sources: lesson student comments, lesson teacher comments, `contact.note` (contact_notes), and `trail.lesson` notes/complete_notes (trail_lesson). Sources 3 & 4 are **optional** — guarded by `'<model>' in self.env`, so they appear only if those modules are installed; they are not declared in the manifest `depends`. Each card is color-coded by type and clicking it opens the underlying record. `trail.lesson` is read with `sudo()` (0 ACL rows). To add another source later, append a block to `_collect_all_comments` producing the same dict shape (display fields + `source`, `student_id`, `group_id`/`group_name`, `date_key`) and add matching `is-<type>` / `type-<type>` CSS colors.

17. **Notes & Comments filtering is server-side (`get_dashboard_comments`).** The feed is filtered in Python over the full collected set (so the display `limit` never hides matches). Filters: free-text comment search, author (name), teacher (`teacher_id`), student/person (`student_id`), training group (`group_id`), source module, and a date range. **The author/teacher/student/group/module filters are multi-value** — you can select several values in one filter (e.g. two teachers) and rows matching ANY of them are kept (OR within a filter, AND across filters). The controls are the `FilterMultiSelect` OWL widget; the backend accepts a list (a bare scalar is auto-wrapped for backward compatibility). **The User Activity panel has its own client-side `Search user…` box** (`activitySearch` → `displayedActivity`), independent of these server-side comment filters. The frontend turns date-mode presets (this year / month / week / between / specific day) into a concrete `date_from`/`date_to`, so the backend only handles a plain inclusive range (compared against each row's `date_key`). Dropdown options (`authors`/`students`/`teachers`/`groups`/`sources`) are returned alongside the data and computed from the FULL set, so selecting one filter never shrinks the others' options. Scope notes: the teacher and group filters only match lesson + (teacher only) trial sources; the student filter matches lesson-student, contact, and trial rows (the "person the note is about"). The filter controls are **custom OWL widgets** (`FilterSelect`/`FilterDate`) — native `<select>`/date popups are not used because their popups can't be styled. The `type_label` is free text — e.g. lesson sources use **"For Student"** / **"For Lesson"** to make the comment's target explicit.

9. **Logout is tracked via a controller.** `controllers/main.py` extends `/web/session/logout` and calls `close_session(uid)` (closes the user's latest open row), stamping `session_end`. This mainly improves duration accuracy; the "one row per entry" guarantee already comes from the per-page-load client token. A logout also reloads the page → next entry gets a new token anyway. **Note:** F5 / manual refresh likewise produces a new token, so a page refresh starts a new session row by design.

10. **UTC → local timezone.** `get_dashboard_activity` and `_collect_all_comments` (via `_fmt_comment_date`) use `fields.Datetime.context_timestamp` to convert to the requesting user's timezone before formatting. The dashboard shows local times throughout.

11. **Clear button is admin-only and irreversible.** `clear_activity_logs` raises `AccessError` unless the caller is in `base.group_system`, then deletes every `user.login.log` row. Use it to reset noisy/duplicate test data; sessions repopulate as users send heartbeats.

12. **`duration_display` is a non-stored computed field.** Recomputed on every read — acceptable given low log volume per user/day.

13. **Odoo 18 client action pattern.** The `ir.actions.client` tag `staff_dashboard.Dashboard` must exactly match the string registered via `registry.category("actions").add(...)` in `dashboard.js`. The whole dashboard is client-side OWL — no server-rendered view.

14. **Menu icon file may be missing.** `menu.xml` references `staff_dashboard,static/description/icon.png` but no `static/description/` exists. Odoo falls back to a default icon without error.
