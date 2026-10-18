# hr_employee_custom — Module Map

**Odoo 18 | HR extension | Custom teacher profile: study info, languages known, experience/certificates (OWL combo tables), availability**

Depends: `hr`, `hr_skills`, `trail_lesson`, `training_management`

> **Niyə `trail_lesson`:** experience/certificate sətirləri onun lookup-larını təkrar istifadə edir — `place_id`→`trail.lesson.config.company`, `role_id`→`trail.lesson.config.position`, `issued_by_id`→`trail.lesson.config.school` (eyni zamanda `x_school_id` də ona istinad edir).
> **Niyə `training_management`:** müəllimin tədris qruplarını (`training.group.teacher_id`) göstərmək və "aktiv qrupu var/yox" filtri üçün.

---

## File Tree

```
hr_employee_custom/
├── __manifest__.py                  → adds web.assets_backend (OWL table widget)
├── __init__.py
├── security/
│   └── ir.model.access.csv
├── models/
│   ├── __init__.py
│   ├── hr_employee.py               → adds custom fields to hr.employee
│   ├── language_level.py            → hr.language.level lookup model
│   ├── employee_availability.py     → hr.employee.availability schedule model
│   ├── hr_language.py               → hr.language lookup (NEW)
│   ├── hr_certificate_type.py       → hr.certificate.type lookup (NEW)
│   ├── hr_faculty.py                → hr.faculty lookup (NEW)
│   ├── hr_employee_language.py      → hr.employee.language (language_id + level_id)
│   ├── hr_employee_experience.py    → hr.employee.experience (place_id/role_id/duration, by `kind`)
│   └── hr_employee_certificate.py   → hr.employee.certificate (certificate_id/issued_by_id/year)
├── views/
│   └── hr_employee_views.xml        → standalone views for hr.language.level +
│                                       multiple inherited views for hr.employee form
└── static/src/
    ├── js/employee_table_widget.js  → OWL EmployeeTableBase + 5 subclasses (one2many field widgets)
    ├── xml/employee_table_widget.xml → QWeb hr_employee_custom.EmployeeTable
    └── css/employee_table.css
```

---

## Models

### hr.language.level (`language_level.py`)

Lookup model for teaching language levels (e.g., A1, B2, C1).

`_description = 'Language Level'`  
`_order = 'name'`

| Field    | Type              | Notes              |
|----------|-------------------|--------------------|
| `name`   | Char              | string='Level', required=True |
| `active` | Boolean           | default=True       |

---

### hr.employee.availability (`employee_availability.py`)

Per-employee weekly schedule slots.

`_description = 'Employee Availability'`  
`_order = 'day_of_week, time_from'`

| Field         | Type      | Notes                                              |
|---------------|-----------|----------------------------------------------------|
| `employee_id` | Many2one → hr.employee | required=True, ondelete='cascade'    |
| `day_of_week` | Selection | required=True; '0'=Monday … '6'=Sunday             |
| `time_from`   | Float     | required=True; 24h format; displayed with `float_time` widget |
| `time_to`     | Float     | required=True; 24h format; displayed with `float_time` widget |

---

### hr.language (`hr_language.py`) — NEW lookup

`name` (Char, required) + `active`. Languages the teacher can know. The OWL combo creates new entries on the fly.

### hr.certificate.type (`hr_certificate_type.py`) — NEW lookup

`name` (Char, required) + `active`. Certificate names (IELTS, TOEFL, CELTA…). Combo-creatable.

### hr.faculty (`hr_faculty.py`) — NEW lookup

`name` (Char, required) + `active`. Faculties. Bound to `x_faculty_id` as a standard form Many2one (Odoo native dropdown + "Create"). University is the existing `x_school_id` → `trail.lesson.config.school` lookup.

> **Reused lookups (from `trail_lesson`, not redefined here):** `trail.lesson.config.company` (Place), `trail.lesson.config.position` (Role/What), `trail.lesson.config.school` (Issued By). Plus the in-module `hr.language.level` (Level). All already have full CRUD for `base.group_user`, so combo quick-create works.

---

### hr.employee.language (`hr_employee_language.py`)

One line = one language the teacher knows + its level. Edited via the OWL `employee_language_table` widget (both columns are **combo** = select-or-create).

| Field | Type | Notes |
|---|---|---|
| `employee_id` | Many2one → hr.employee | required, ondelete='cascade' |
| `language_id` | Many2one → hr.language | combo (select / create) |
| `level_id` | Many2one → hr.language.level | combo (select / create) |

---

### hr.employee.experience (`hr_employee_experience.py`)

Unified model for **work / volunteer / english-teaching** experience — split by `kind`. One model feeds three One2many fields (each domain-filtered by `kind`); the OWL widget sets `kind` on create.

| Field | Type | Notes |
|---|---|---|
| `employee_id` | Many2one → hr.employee | required, ondelete='cascade' |
| `kind` | Selection | work / volunteer / english_teaching; required, default work |
| `place_id` | Many2one → trail.lesson.config.company | where (combo) |
| `role_id` | Many2one → trail.lesson.config.position | what they did (combo) |
| `duration` | Char | how long (free text) |

---

### hr.employee.certificate (`hr_employee_certificate.py`)

| Field | Type | Notes |
|---|---|---|
| `employee_id` | Many2one → hr.employee | required, ondelete='cascade' |
| `certificate_id` | Many2one → hr.certificate.type | combo (select / create) |
| `issued_by_id` | Many2one → trail.lesson.config.school | combo (select / create) |
| `year` | Char | free text |

---

### hr.employee (`hr_employee.py`) — HrEmployee extension

All custom fields use `x_` prefix (Odoo convention for custom/studio fields).

| Field                  | Type                              | Notes                                      |
|------------------------|-----------------------------------|--------------------------------------------|
| `x_language_levels`    | Many2many → hr.language.level     | relation='hr_employee_language_level_rel'; string='Teaching Levels' (which CEFR levels the teacher can **teach** — distinct from `x_language_line_ids` below) |
| `x_school_id`          | Many2one → trail.lesson.config.school | string='School / University' (= University lookup) |
| `x_faculty_id`         | Many2one → hr.faculty             | string='Faculty' (native dropdown + Create) |
| `x_study_year`         | Selection                         | 1..5 + graduate; string='Course / Year'    |
| `x_lesson_type`        | Selection                         | individual / group / both; string='Lesson Type' |
| `x_availability_ids`   | One2many → hr.employee.availability | string='Available Days & Hours'          |
| `x_start_date`         | Date                              | string='Start Date'                        |
| `x_notes`              | Html                              | string='Notes'                             |
| `x_language_line_ids`  | One2many → hr.employee.language    | "Languages Known" (OWL `employee_language_table`) |
| `x_work_exp_ids`       | One2many → hr.employee.experience  | domain `kind=work` (OWL `employee_work_table`) |
| `x_volunteer_ids`      | One2many → hr.employee.experience  | domain `kind=volunteer` (OWL `employee_volunteer_table`) |
| `x_has_english_teaching` | Boolean                         | gate for the english-teaching section       |
| `x_english_teaching_ids` | One2many → hr.employee.experience | domain `kind=english_teaching`; view-invisible unless the boolean (OWL `employee_english_table`) |
| `x_certificate_ids`    | One2many → hr.employee.certificate | "Certificates" (OWL `employee_certificate_table`) |
| `x_strong_skills`      | Html                              | string='Strong Skills & Knowledge'          |
| `x_group_ids`          | One2many → training.group (via `teacher_id`) | the teacher's training groups (read-only "Training Groups" tab) |
| `x_active_group_count` | Integer (compute, store)          | count of the teacher's groups in state `in_progress` |
| `x_has_active_group`   | Boolean (compute, store)          | True if any group is `in_progress`; **searchable** — backs the employee filter |

**`_compute_active_groups()`** (`@api.depends('x_group_ids.state')`, stored): counts `x_group_ids` with `state == 'in_progress'` → sets `x_active_group_count` + `x_has_active_group`. Stored so the search filter works; recomputes when a group is created/reassigned or its state changes (e.g. `training.group.action_start()`). "Active" = group state **Started** (`in_progress`); Waiting/Completed = passive.

> **Removed** (per requirements): `x_demo_result` (Demo Lesson Result) and `x_payment_condition` (Salary / Payment Terms) — both dropped from the model and the form. A module upgrade leaves their DB columns orphaned but unused.

### OWL field widget (`static/src/`)

`EmployeeTableBase` (template `hr_employee_custom.EmployeeTable`) renders any line One2many as an editable table: header from `config.columns`, one cell control per column, a per-row delete, and an Add button. It works like `contact_notes` — **direct ORM RPC** (`searchRead`/`create`/`write`/`unlink`) keyed off `record.resId`, so edits save **immediately** (outside the form Save/Discard cycle). `useEffect` on `resId` reloads when a brand-new employee is first saved; before that it shows "Save the employee first." Five subclasses set only their `config` (model, `parentField`, `fixed` defaults like `{kind:'work'}`, columns, addLabel) and are registered in the `fields` registry as `employee_language_table` / `employee_work_table` / `employee_volunteer_table` / `employee_english_table` / `employee_certificate_table` (all `supportedTypes: ['one2many']`).

**Column types:**
- `char` — plain text `<input>` (`onCell` writes immediately).
- `combo` — **select-or-create** lookup, rendered by the child component **`EmployeeCombo`** (template `hr_employee_custom.EmployeeCombo`), styled to match the staff-dashboard filter dropdown (`o_ecombo*` classes mirror `o_fsel*`: rounded trigger + caret, shadowed menu, search box, hover/active highlight). NOT the native `<datalist>` (looked foreign). Behaviour: open → type in the search box → filtered options below; clicking an option calls `onComboChoose` (writes the m2o id). If the typed text has no exact match, an Odoo-style **`Create "<typed text>"`** row appears (green, shows the literal text) → click (or Enter) calls `onComboCreate` → `orm.create(col.model, [{name}])`, refreshes options, links the new id. A **Clear** row removes the value (`onComboClear`). Stored as the line's Many2one id; displayed as the option name (`cellText` unwraps `[id,name]`).
- `m2o` — (removed from the template; `combo` is used for all lookups).

**Cross-module dependency:** `x_school_id` references `trail.lesson.config.school` from the `trail_lesson` module — that module must be installed first.

---

## Views (`hr_employee_views.xml`)

### Standalone views for `hr.language.level`

| View ID                    | Type   | Description                               |
|----------------------------|--------|-------------------------------------------|
| `view_language_level_tree` | list   | Shows `name` column                       |
| `view_language_level_form` | form   | Sheet with `name` (Level) and `active`    |
| `action_language_level`    | action | act_window; view_mode=list,form           |
| `menu_language_level_config` | menuitem | Parent: `hr.menu_config_employee`; sequence=20; label "Language Level Configurator" |

### Standalone views for the new lookups

- `view_hr_language_tree` (editable list) + `action_hr_language` + `menu_hr_language_config` ("Languages", seq 21) under `hr.menu_config_employee`.
- `view_hr_certificate_type_tree` (editable list) + `action_hr_certificate_type` + `menu_hr_certificate_type_config` ("Certificate Types", seq 22) under `hr.menu_config_employee`.
- `view_hr_faculty_tree` (editable list) + `action_hr_faculty` + `menu_hr_faculty_config` ("Faculties", seq 23) under `hr.menu_config_employee`.
- The reused `trail.lesson.config.*` lookups keep their own Configurator menus inside the Trail Lesson app.

### Inherited views for `hr.employee` (all inherit `hr.view_employee_form`)

#### 1. `view_employee_form_teacher_main`
Main customisation. Uses `position="replace"` on `//sheet/group` to completely replace the default employee form body with a teacher-specific layout:

**Header additions (`position="inside"` on `//header`):**
- Save button (`special="save"`, class `btn-primary`)
- Cancel button (`special="cancel"`, class `btn-secondary`)

**Hidden standard fields** (set `invisible="1"` via xpath attributes):
- `department_id`, `parent_id`, `coach_id`, `job_title`, `job_id`
- Button `type='action' name='250'` (Archive/Send action)

**Replaced sheet group layout:**

| Group heading              | Fields shown                                                                 |
|----------------------------|------------------------------------------------------------------------------|
| Contact Information        | `work_phone` (Phone), `mobile_phone` (WhatsApp), `work_email`, `private_email`, `private_phone` — all with appropriate phone/email widgets |
| Personal Information       | `birthday` (Date of Birth), `x_school_id`, `x_faculty`, `x_study_year`, `certificate` (Education Level) |
| Teacher Information (left) | `x_language_levels` (many2many_tags), `x_lesson_type`                        |
| Teacher Information (right)| `x_start_date`, `x_active_group_count` (readonly), `category_ids` (Tags, many2many_tags) |
| Available Days & Hours     | `x_availability_ids` inline editable list with `day_of_week`, `time_from` (float_time), `time_to` (float_time) |

**Added notebook tabs** (`position="inside"` on `//notebook`):
- Page `x_teacher_questions_tab` "Teacher Questions" — `<separator>`-grouped sections: Languages Known (`x_language_line_ids`), Work Experience (`x_work_exp_ids`), Volunteer Experience (`x_volunteer_ids`), English Teaching (`x_has_english_teaching` checkbox + `x_english_teaching_ids`, the table `invisible="not x_has_english_teaching"`), Certificates (`x_certificate_ids`), and Strong Skills & Knowledge (`x_strong_skills` Html). The five line tables use the OWL widgets above.
- Page `x_groups_tab` "Training Groups" — read-only list of `x_group_ids` (the teacher's `training.group` records): columns name / start date / lesson count / student count / `state` (badge: Started=green/success, Waiting=warning, Completed=muted) so active vs passive is visible at a glance.
- Page `x_notes_tab` "Notes" — contains `x_notes` Html field with placeholder text

**Inherited search view** `view_employee_filter_active_group` (inherits `hr.view_employee_filter`) adds two filters: **Has Active Group** (`x_has_active_group = True`) and **No Active Group** (`= False`) — lets you filter employees by whether the teacher currently has a Started group.

#### 2. `view_employee_hide_resume`
Hides the standard `public` tab (Resume/Skills tab from `hr_skills`).

#### 3. `view_employee_hide_hr_settings`
Hides the standard `hr_settings` tab (HR Settings tab).

#### 4. `view_employee_hide_personal_info`
Hides the standard `personal_information` tab (Private Information tab).

> **Net result:** The employee form only shows the custom teacher layout in the sheet, plus the custom "Notes" tab in the notebook. The three standard tabs (Resume, HR Settings, Private Information) are all hidden.

---

## Security (`security/ir.model.access.csv`)

| ID                                   | Model                      | Group                  | R | W | C | D |
|--------------------------------------|----------------------------|------------------------|---|---|---|---|
| `access_language_level_user`         | `hr.language.level`        | `base.group_user`      | 1 | 1 | 1 | 0 |
| `access_language_level_manager`      | `hr.language.level`        | `hr.group_hr_manager`  | 1 | 1 | 1 | 1 |
| `access_employee_availability_user`  | `hr.employee.availability` | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_employee_language_user`      | `hr.employee.language`     | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_employee_experience_user`    | `hr.employee.experience`   | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_employee_certificate_user`   | `hr.employee.certificate`  | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_hr_language_user`            | `hr.language`              | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_hr_certificate_type_user`    | `hr.certificate.type`      | `base.group_user`      | 1 | 1 | 1 | 1 |
| `access_hr_faculty_user`             | `hr.faculty`               | `base.group_user`      | 1 | 1 | 1 | 1 |

> The line models and the two new lookups need full CRUD for `base.group_user` because the OWL widget writes them via direct ORM RPC (create/write/unlink) as the regular user. `hr.language.level` user perm was bumped to **create** (was read-only) so the combo can quick-create levels too (unlink still manager-only). The reused `trail.lesson.config.*` lookups already grant full CRUD to `base.group_user`.

**Notes:**
- Regular users can only **read** language levels; only HR Managers can create/edit/delete them.
- All users have full CRUD on availability slots (needed for inline editing in the employee form).
- No explicit ACL for `hr.employee` — access is inherited from the base `hr` module.

---

## Important Notes

- All custom fields use `x_` prefix — Odoo convention for custom/studio fields, avoids naming collisions.
- `x_language_levels` uses an explicit Many2many relation table (`hr_employee_language_level_rel`) — not auto-generated.
- The `hr.language.level` model is a standalone configurable lookup, separate from any `english_level` Selection on `trail_lesson` models — allows flexible level management via UI.
- `x_school_id` creates a hard dependency on the `trail_lesson` module (must be installed first); the manifest does **not** declare this in `depends` — this is an implicit/runtime dependency.
- The form view uses `position="replace"` on the main sheet group, meaning the entire default `hr.employee` field layout is discarded and replaced — not extended.
- Three standard employee tabs (`public`/Resume, `hr_settings`, `personal_information`) are each hidden by separate inherited view records, keeping the customisation modular.
- No ORM method overrides (`@api.onchange`, `create`, `write`, etc.) — pure field additions and view customisation.
- Module is marked `application=False` — it is an extension, not a standalone app.
