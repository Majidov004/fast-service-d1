# contact_customization — Module Map

**Odoo 18 | Functional/Technical | Applicant & Student contact management with trial lesson assessment**

Depends: `base`, `contacts`, `hr`, `trail_lesson`, `lesson_record`

> **Yeni (Tələbə-Qrup + Meeting):** `res_partner_common`-a `training_group_count` smart button (`action_view_training_groups` → tələbənin `training.group`-ları) və `meeting_line_ids` + `get_meeting_comments()` (tələbənin yalnız şərhi olan `lesson.student.line` qeydləri, qrupa görə) əlavə olundu. Meeting tab OWL `meeting_comments_widget` (`static/src/`) ilə kart-stildə göstərir. Buna görə modul artıq `lesson_record` (→ `training_management`) modulundan asılıdır.

---

## File Tree

```
contact_customization/
├── __manifest__.py                          → Module metadata, dependencies, data file list
├── __init__.py                              → Imports models and wizards packages
├── models/
│   ├── __init__.py                          → Imports all four model files (ir_ui_menu commented out)
│   ├── res_partner_common.py                → Shared fields for both Applicant and Student (identity flags, profile, trial lesson linkage, tl_ related fields)
│   ├── res_partner_applicant.py             → Applicant workflow: applicant_state, status transitions, activity creation, trial lesson proxy actions
│   ├── res_partner_student.py               → Student workflow: lead_state, is_waiting_student
│   ├── trail_lesson_complete_wizard.py      → Waiting-student hook on the trial wizard (paid + starts later → Student)
│   ├── training_student_line.py             → Qrupa yazılanda is_waiting_student söndürülür
│   └── res_partner_trial_fields.py          → Quick-plan fields: trial_teacher_id, trial_datetime
├── wizards/
│   ├── __init__.py                          → Imports planned_remember_wizard
│   └── planned_remember_wizard.py           → TransientModel to set planned_remember state with date and employee
├── views/
│   ├── res_partner_form_view.xml            → Inherits base contact form: header buttons, status bars, smart button, field groups, Trial Lesson tab, Trial Detail tab
│   ├── res_partner_filter_view.xml          → Inherits base search view: adds Notes/comment search field
│   ├── applicant_views.xml                  → Standalone list/kanban/search views + action + menu for Applicants
│   ├── student_views.xml                    → Standalone list/kanban/search views + action for Students
│   ├── planned_remember_views.xml           → List view + action + menu for Planned Remember applicants
│   ├── waiting_student_views.xml            → List + search + action + menu for Waiting Students
│   └── planned_remember_wizard_view.xml     → Form view for PlannedRememberWizard dialog
├── security/
│   └── ir.model.access.csv                  → Access rights for the wizard transient model only
└── static/
    └── src/
        ├── css/meeting_comments.css         → Meeting tab card styling
        ├── js/meeting_comments_widget.js    → OWL MeetingCommentsWidget (one2many field widget)
        └── xml/meeting_comments_widget.xml  → QWeb template contact_customization.MeetingCommentsWidget
```

---

## Models

All four files use `_inherit = 'res.partner'` — no new technical names are defined. Odoo merges all extensions into the same `res.partner` ORM class at registry time.

---

### `res_partner_common.py` — ResPartnerCommon

**_inherit:** `res.partner`

#### Identity Flags

| Field | Type | Default | Notes |
|---|---|---|---|
| `is_student` | Boolean | False | Marks this partner as a student |
| `is_applicant` | Boolean | False | Marks this partner as an applicant |

#### Shared Profile Fields

| Field | Type | Notes |
|---|---|---|
| `manager_id` | Many2one `hr.employee` | Labeled "Registrar"; auto-defaults to current user's `employee_id` via `default_get` |
| `teacher_id` | Many2one `hr.employee` | Assigned teacher; visible only on student form (`invisible="not is_student"`) |
| `expected_join_date` | Date | tracking=True; synced from trial lesson join timing via onchange |
| `current_level` | Selection | CEFR language level: `a1`→A1 Beginner, `a2`→A2 Elementary, `b1`→B1 Pre-Intermediate, `b2`→B2 Intermediate, `c1`→C1 Advanced, `c2`→C2 Proficiency |
| `reference_source` | Selection | 13 values: `tiktok_organic`, `tiktok_ads`, `instagram_organic`, `instagram_ads`, `facebook_organic`, `facebook_ads`, `whatsapp`, `linkedin_organic`, `linkedin_ads`, `youtube_organic`, `youtube_ads`, `acquaintance`, `mail` |
| `reference_tiktok_account` | Char | TikTok Account Name; shown only when `reference_source in ('tiktok_organic', 'tiktok_ads')` |
| `reference_instagram_account` | Char | Instagram Account Name; shown only when `reference_source in ('instagram_organic', 'instagram_ads')` |
| `reference_facebook_account` | Char | Facebook Account Name; shown only when `reference_source in ('facebook_organic', 'facebook_ads')` |
| `reference_whatsapp_account` | Char | WhatsApp Number; shown only when `reference_source == 'whatsapp'` |
| `reference_linkedin_account` | Char | LinkedIn Profile URL; shown only when `reference_source in ('linkedin_organic', 'linkedin_ads')` |
| `reference_youtube_account` | Char | YouTube Channel Name; shown only when `reference_source in ('youtube_organic', 'youtube_ads')` |

#### Trial Lesson Smart Button Fields

| Field | Type | Notes |
|---|---|---|
| `trail_lesson_count` | Integer (compute) | Count of `trail.lesson` records with `student_id = rec.id`; not stored; `@api.depends()` is empty |
| `trial_lesson_id` | Many2one `trail.lesson` (compute) | Most recent trial lesson ordered by `lesson_datetime desc`, limit 1; `store=False`; `@api.depends()` is empty |

#### tl_ Related Fields (all `readonly=True` unless noted)

All related from `trial_lesson_id` on the most recent `trail.lesson` record.

| Field | Type | Related Path | Notes |
|---|---|---|---|
| `tl_gender` | Selection | `trial_lesson_id.gender` | |
| `tl_approximate_age` | Selection | `trial_lesson_id.approximate_age` | |
| `tl_company_id` | Many2one `trail.lesson.config.company` | `trial_lesson_id.lesson_company_id` | |
| `tl_position_id` | Many2one `trail.lesson.config.position` | `trial_lesson_id.position_id` | |
| `tl_school_id` | Many2one `trail.lesson.config.school` | `trial_lesson_id.school_id` | |
| `tl_learning_purpose_id` | Many2one `trail.lesson.config.learning.purpose` | `trial_lesson_id.learning_purpose_id` | |
| `tl_course_id` | Many2one `trail.lesson.config.course` | `trial_lesson_id.course_id` | |
| `tl_english_level` | Selection | `trial_lesson_id.english_level` | |
| `tl_for_whom` | Selection | `trial_lesson_id.for_whom` | |
| `tl_for_whom_note` | Char | `trial_lesson_id.for_whom_note` | |
| `tl_comprehension` | Selection | `trial_lesson_id.comprehension` | |
| `tl_motivation` | Selection | `trial_lesson_id.motivation` | |
| `tl_previous_courses` | Boolean | `trial_lesson_id.previous_courses` | |
| `tl_decision` | Selection | `trial_lesson_id.decision` | Used as gate for "Trial Detail" tab visibility |
| `tl_thinking_reason` | Selection | `trial_lesson_id.thinking_reason` | |
| `tl_system_choice` | Selection | `trial_lesson_id.system_choice` | |
| `tl_system_choice_note` | Char | `trial_lesson_id.system_choice_note` | |
| `tl_lesson_format` | Selection | `trial_lesson_id.lesson_format` | |
| `tl_payment_type` | Selection | `trial_lesson_id.payment_type` | |
| `tl_payment_amount` | Float | `trial_lesson_id.payment_amount` | |
| `tl_join_timing` | Selection | `trial_lesson_id.join_timing` | **`readonly=False`** — the only writable tl_ related field |
| `tl_expected_join_date` | Date | `trial_lesson_id.expected_join_date` | |
| `tl_complete_notes` | Text | `trial_lesson_id.complete_notes` | |
| `tl_qa_ids` | Many2many `trail.lesson.qa` (compute) | `trial_lesson_id.qa_ids` | Computed via `@api.depends('trial_lesson_id')` |

#### Methods

**`default_get(fields_list)`** (`@api.model`):
After calling `super().default_get()`, checks if `manager_id` is absent from the result. If so, reads `self.env.user.employee_id` and sets it as the default. This means the registrar field is pre-populated with the current user's employee record on every new partner.

**`_compute_trail_lesson_count()`** (`@api.depends()`):
Iterates self; for each record calls `search_count([('student_id', '=', rec.id)])` on `trail.lesson`. The empty `@api.depends()` means this does NOT auto-recompute when lessons are added/removed — a form save or manual refresh is needed.

**`action_view_trail_lessons()`**:
Returns an `ir.actions.act_window` opening `trail.lesson` in list+form view mode, filtered by `student_id = self.id`, with `default_student_id` in context.

**`_compute_trial_lesson_id()`** (`@api.depends()`):
For each record, searches `trail.lesson` with `student_id = rec.id`, ordered by `lesson_datetime desc`, limit 1. Empty depends — same non-reactive caveat as above.

**`_compute_tl_qa_ids()`** (`@api.depends('trial_lesson_id')`):
Copies `qa_ids` from `trial_lesson_id` into the computed Many2many. Returns empty recordset if no trial lesson.

**`_onchange_tl_join_timing_remember()`** (`@api.onchange('tl_join_timing')`):
Fires when `tl_join_timing` changes in the UI. Only acts when `self.applicant_state == 'remember'` and `tl_join_timing` is set. Copies `self.tl_expected_join_date` into `self.expected_join_date`. This is the fix for synchronizing the expected join date when a "remember" applicant selects a join timing.

#### Training Group & Meeting (Student) Fields & Methods

| Field | Type | Notes |
|---|---|---|
| `training_group_count` | Integer (compute) | Count of `training.group` records where `student_line_ids.student_id == self`. `@api.depends()` is empty → non-reactive (recomputes on load/refresh). |
| `meeting_line_ids` | One2many `lesson.student.line` (via `student_id`) | Attach point for the `meeting_comments_widget`; the widget ignores its data and calls `get_meeting_comments()` instead. |

**`_compute_training_group_count()`** (`@api.depends()`): `search_count` on `training.group` with domain `[('student_line_ids.student_id', '=', rec.id)]`.

**`action_view_training_groups()`** (`ensure_one`): Returns an `ir.actions.act_window` opening `training.group` (list,form) with domain `[('student_line_ids.student_id', '=', self.id)]` — the groups the student is enrolled in. Backs the **Training Groups** smart button.

**`get_meeting_comments()`** (`ensure_one`): Searches `lesson.student.line` where `student_id == self` AND `comment` is set (non-empty). Groups results by the lesson's `group_id` and returns a list of dicts: `{group_id, group_name, teacher_name, lessons: [{id, lesson_name, lesson_number, date (dd-mm-YYYY), date_sort, attendance, comment}]}`. Lessons inside each group are sorted by date desc. Called by the OWL `meeting_comments_widget` via `orm.call`. Only lessons WITH a comment for this student appear (by design).

---

### `res_partner_applicant.py` — ResPartnerApplicant

**_inherit:** `res.partner`

#### Fields

| Field | Type | Notes |
|---|---|---|
| `applicant_state` | Selection | 11 values; tracking=True (see table below) |
| `planned_remember_date` | Date | Set by the PlannedRememberWizard; tracking=True |
| `planned_remember_employee_id` | Many2one `hr.employee` | Employee who scheduled the remember; tracking=True |
| `no_answer_type` | Selection | 3 values; sub-classification for "no answer" situations; tracking=True |
| `no_answer_type_effective` | Selection (compute) | Unified display field; not stored |

**`applicant_state` values:**

| Value | Label |
|---|---|
| `interested` | Interested |
| `needs_to_be_called` | Needs to be Called |
| `called` | Messaged |
| `wait` | Wait |
| `no_answer` | No Answer |
| `planned_trial` | Planned Trial |
| `trial_no_contact` | Trial – No Contact (legacy; no current method sets this value) |
| `planned_remember` | Planned Remember |
| `remember` | Remember |
| `not_want` | Not Want |
| `paid` | Paid |

**`no_answer_type` values:**

| Value | Label |
|---|---|
| `message_not_answered` | Message is not answered |
| `before_trial` | Before Trial Lesson |
| `after_trial` | After Trial Lesson |

#### Methods

**`_compute_no_answer_type_effective()`** (`@api.depends('applicant_state', 'no_answer_type')`):
- If `applicant_state == 'trial_no_contact'` → always `'before_trial'`
- If `applicant_state == 'no_answer'` and `no_answer_type` is set → mirrors `no_answer_type`
- Otherwise → `False`

This field unifies two situations (legacy `trial_no_contact` state and current `no_answer+before_trial` combination) into a single displayable badge value.

**`create(vals_list)`** (`@api.model_create_multi`):
For each dict in `vals_list`: if `is_applicant` is True and `applicant_state` is not provided, sets `applicant_state = 'interested'`. After `super().create()`, filters the new records for applicants and calls `_create_applicant_activity()`.

**`_create_applicant_activity()`**:
Internal helper. Resolves the activity type via `mail.mail_activity_data_call` ref; falls back to searching for a type with "call" in the name; then to any available type. For each applicant record in self that does not already have that activity scheduled, calls `rec.activity_schedule()` with summary "Call applicant: {name}" and a note. Prevents duplicate activities by checking existing ones first.

**`action_open_planned_remember_wizard()`**:
`ensure_one()`. Returns an `ir.actions.act_window` opening `res.partner.planned.remember.wizard` form in `target='new'` (dialog), passing `default_partner_id = self.id` in context.

**Status Transition Methods** (all iterate `for rec in self`):

| Method | Sets `applicant_state` | Other side effects |
|---|---|---|
| `action_set_wait()` | `wait` | None |
| `action_set_needs_to_be_called()` | `needs_to_be_called` | Raises `UserError` if `trial_teacher_id` is not set |
| `action_set_called()` | `called` | Marks all `mail.activity` on `res.partner` for this record as done |
| `action_set_no_answer()` | `no_answer` | Sets `no_answer_type = 'message_not_answered'` |
| `action_set_trial_no_contact()` | **`no_answer`** | Sets `no_answer_type = 'before_trial'` — does NOT set `trial_no_contact` state |
| `action_set_remember()` | `remember` | None |
| `action_set_not_want()` | `not_want` | Marks ALL `activity_ids` as done |
| `action_set_paid()` | `paid` | `is_applicant = False`, `is_student = True`, marks all activities done |

**Trial Lesson Proxy Methods** (all `ensure_one()`, raise `UserError` if `trial_lesson_id` is False):

| Method | Delegates to |
|---|---|
| `action_trial_complete()` | `self.trial_lesson_id.action_complete()` |
| `action_trial_missing()` | `self.trial_lesson_id.action_missing()` |
| `action_trial_plan_new()` | `self.trial_lesson_id.action_plan_new_trial()` |

**`action_create_trial_lesson()`**:
Iterates self. Raises `UserError` if `trial_teacher_id` is not set. Creates a `trail.lesson` record with:
- `student_id = rec.id`
- `teacher_id = rec.trial_teacher_id.id`
- `lesson_datetime = rec.trial_datetime`

If `trial_datetime` is set, calls `lesson.action_schedule()` on the newly created lesson. Sets `applicant_state = 'planned_trial'`. By design, does NOT open the trial lesson form automatically after creation.

---

### `res_partner_student.py` — ResPartnerStudent

**_inherit:** `res.partner`

| Field | Type | Default | Notes |
|---|---|---|---|
| `lead_state` | Selection | `lesson_not_planned` | tracking=True; values: `lesson_not_planned`, `lesson_planned`, `lesson_complete` |
| `is_waiting_student` | Boolean | `False` | tracking=True — **Gözləyən tələbə**: ödəniş edib, amma sonra başlayır; qrupa yazılanda avtomatik söndürülür |

**Methods:**

**`action_set_lesson_planned()`**: Sets `lead_state = 'lesson_planned'` for all records in self.

**`action_set_lesson_complete()`**: Sets `lead_state = 'lesson_complete'` for all records in self.

⚠️ `action_set_lesson_planned()` hələ də mövcuddur, amma **heç bir view-dan çağırılmır** ("Plan Lesson" düyməsi silinib) — yəni `lead_state` artıq `lesson_not_planned`-dan öz-özünə çıxmır.

---

### `trail_lesson_complete_wizard.py` — TrailLessonCompleteWizardWaiting

**_inherit:** `trail.lesson.complete.wizard` (TransientModel)

`action_confirm()` override → `super()` sonrası `_apply_waiting_student()`:
əgər `decision == 'joining'`, `join_timing != 'now'` **və** `payment_amount > 0` isə
partner → `is_student=True`, `is_waiting_student=True`, `expected_join_date` yazılır;
applicant idisə `is_applicant=False` + `applicant_state='paid'` + activity-lər bağlanır + chatter qeydi.

> Baza modul (trail_lesson) belə halda yalnız `applicant_state='remember'` edirdi —
> bu override ödəniş edən "sonra gələn" adamı **tələbə** kimi qeyd edir.

---

### `training_student_line.py` — TrainingStudentLine

**_inherit:** `training.student.line`

`create()` / `student_id` dəyişən `write()` → həmin tələbənin `is_waiting_student` bayrağını söndürür
(qrupa düşdüyü an gözləmə bitir).

---

### `res_partner_trial_fields.py` — ResPartnerTrialFields

**_inherit:** `res.partner`

| Field | Type | Notes |
|---|---|---|
| `trial_teacher_id` | Many2one `hr.employee` | Teacher to be used in the upcoming trial lesson |
| `trial_datetime` | Datetime | Scheduled date and time for the trial lesson |

No methods. These fields are used exclusively by `action_create_trial_lesson()` in `res_partner_applicant.py` to pre-populate the `trail.lesson` record at creation time.

---

## Wizards

### `res.partner.planned.remember.wizard` — `wizards/planned_remember_wizard.py`

**_name:** `res.partner.planned.remember.wizard`
**_description:** `Planned Remember Wizard`
TransientModel — records are deleted after the session ends.

| Field | Type | Required | Notes |
|---|---|---|---|
| `partner_id` | Many2one `res.partner` | Yes | Passed via `default_partner_id` from context; hidden in the form |
| `employee_id` | Many2one `hr.employee` | Yes | `readonly=True`; defaults to `self.env.user.employee_id` via lambda |
| `planned_date` | Date | Yes | The date on which the follow-up is planned |

**`action_confirm()`** (`ensure_one()`):
Writes three fields on `self.partner_id`:
- `applicant_state = 'planned_remember'`
- `planned_remember_date = self.planned_date`
- `planned_remember_employee_id = self.employee_id.id`

Returns an `ir.actions.act_window` with `target='current'` opening the partner's form view (`res_id = self.partner_id.id`), effectively closing the dialog and navigating back to the contact.

---

## Views

### `views/res_partner_form_view.xml`

Two separate `ir.ui.view` records, both inheriting `base.view_partner_form`.

---

**Record 1: `view_partner_form_custom`** (id: `view_partner_form_custom`)

- Adds stat buttons `position="inside"` the `//div[@name='button_box']` (no longer touches the calendar-provided `schedule_meeting` button — `calendar` was removed, so that button no longer exists):
  - **Stat button** `action_view_trail_lessons` — icon `fa-graduation-cap`, shows `trail_lesson_count` via `statinfo` widget labeled "Trial Lessons".
  - **Stat button** `action_view_training_groups` — icon `fa-users`, shows `training_group_count` via `statinfo` labeled "Training Groups"; `invisible="not is_student"`.
- Injects a `<header>` block before `<sheet>`. All button visibility uses Odoo 18 Python expression strings:

  **Applicant workflow buttons:**
  | Button Label | Method | Class | Visible when |
  |---|---|---|---|
  | Needs to be Called | `action_set_needs_to_be_called` | btn-primary | `applicant_state == 'interested' and is_applicant` |
  | Messaged | `action_set_called` | btn-primary | `applicant_state == 'needs_to_be_called' and is_applicant` |
  | No Answer | `action_set_no_answer` | btn-secondary | `applicant_state == 'needs_to_be_called' and is_applicant` |
  | Wait | `action_set_wait` | btn-warning | `applicant_state == 'called' and is_applicant` |
  | Create Trial Lesson | `action_create_trial_lesson` | btn-primary | `applicant_state in ('called', 'wait') and is_applicant` |
  | Messaged (re-entry) | `action_set_called` | btn-secondary | `applicant_state == 'no_answer' and no_answer_type not in ('before_trial', 'after_trial') and is_applicant` |
  | Complete Trial | `action_trial_complete` | btn-success | `applicant_state == 'planned_trial' and is_applicant` |
  | Missing Lesson | `action_trial_missing` | btn-danger | `applicant_state == 'planned_trial' and is_applicant` (has confirm dialog) |
  | Plan New Trial | `action_trial_plan_new` | btn-secondary | `applicant_state == 'planned_trial' and is_applicant` |
  | Paid | `action_set_paid` | btn-success | `(applicant_state == 'trial_no_contact' or (applicant_state == 'no_answer' and no_answer_type == 'before_trial')) and is_applicant` |
  | Planned Remember | `action_open_planned_remember_wizard` | btn-warning | same as Paid above |
  | Not Want | `action_set_not_want` | btn-danger | same as Paid above |
  | Paid | `action_set_paid` | btn-success | `applicant_state == 'remember' and is_applicant` |
  | Not Want | `action_set_not_want` | btn-danger | `applicant_state == 'remember' and is_applicant` |
  | Create Trial Lesson | `action_create_trial_lesson` | btn-primary | `applicant_state == 'planned_remember' and is_applicant` |
  | Again Planned Remember | `action_open_planned_remember_wizard` | btn-warning | `applicant_state == 'planned_remember' and is_applicant` |
  | Not Want | `action_set_not_want` | btn-danger | `applicant_state == 'planned_remember' and is_applicant` |
  | Save | special=save | btn-primary | `not applicant_state or applicant_state == 'interested'` |
  | Cancel | special=cancel | btn-secondary | `is_applicant` |

  **Student buttons:**
  | Button Label | Method | Class | Visible when |
  |---|---|---|---|
  | Save | special=save | btn-primary | `is_student` |
  | Complete Lesson | `action_set_lesson_complete` | btn-primary | `lead_state == 'lesson_planned' and is_student` |

  **Status bars in header:**
  - `applicant_state` — widget `statusbar`; invisible when not `is_applicant`; `statusbar_visible=""` (shows all)
  - `lead_state` — widget `statusbar`; invisible when not `is_student`; visible steps: `lesson_not_planned,lesson_planned,lesson_complete`

- Replaces `//sheet/group` with a custom group containing:
  - `phone` (widget phone), `mobile` (widget phone), `email` (widget email)
  - `manager_id` (no_create, no_open)
  - `teacher_id` (no_create, no_open) — invisible when not `is_student`
  - `current_level`
  - A `<div class="o_row">` spanning 2 columns with `reference_source` and the conditional social account fields (each shown only when the matching source is selected)
  - `is_student` and `is_applicant` hidden flags (used by other invisible conditions in the view)
  - `planned_remember_date` (readonly) — invisible unless `applicant_state == 'planned_remember'`
  - `planned_remember_employee_id` (readonly, no_open) — invisible unless `applicant_state == 'planned_remember'`
  - `no_answer_type` (hidden)
  - `no_answer_type_effective` — widget `badge`, readonly; invisible unless `applicant_state in ('no_answer', 'trial_no_contact')`
- Hides standard `company_type` and `parent_id` fields.

---

**Record 2: `view_partner_form_custom_tabs`** (id: `view_partner_form_custom_tabs`)

Inserts the following pages **before the first standard notebook page**:

**Trial Lesson tab** (`trial_lesson_tab`):
- `trial_teacher_id` — invisible when `applicant_state` is not set
- `trial_datetime` — invisible when state is `interested` or empty (only shows from `called` onward)

**Trial Detail tab** (`trial_detail_tab`):
- Entire tab is `invisible="not tl_decision"` — hidden until the trial lesson has a decision recorded.
- Contains a nested `<notebook>` with four sub-pages:

  | Sub-page | Fields shown |
  |---|---|
  | Background | `tl_gender`, `tl_approximate_age`, `tl_for_whom`, `tl_for_whom_note` (hidden if `tl_for_whom == 'self'`), `tl_company_id`, `tl_position_id`, `tl_school_id`, `tl_english_level` |
  | Q&A Session | `tl_qa_ids` readonly list with columns: sequence (handle), question, answer, translation |
  | Assessment | `tl_comprehension`, `tl_motivation`, `tl_learning_purpose_id`, `tl_previous_courses`, `tl_course_id` (hidden if not `tl_previous_courses`) |
  | Decision | `tl_decision` (readonly), `tl_thinking_reason` (readonly, hidden unless `tl_decision == 'thinking'`), `tl_lesson_format` (readonly), `tl_join_timing` (readonly unless `applicant_state == 'remember'`), `tl_expected_join_date` (hidden when no timing or timing is `'later'`), Payment group (hidden unless `tl_decision == 'joining'`) with `tl_payment_type` and `tl_payment_amount`, `tl_system_choice` (radio widget, readonly), `tl_system_choice_note` (readonly, hidden unless `tl_system_choice == 'other'`) |
  | Notes | `tl_complete_notes` — readonly text widget |

Also inserts (before the first standard page, after Trial Detail):
- **Meeting tab** (`meeting_tab`, `invisible="not is_student"`): a single `meeting_line_ids` field rendered with the OWL `meeting_comments_widget` (`nolabel="1"`). Shows the student's per-lesson comments grouped by training group (card style, like the Notes tab). Data comes from `get_meeting_comments()`, not from the One2many itself.

Appends at the **end of the standard notebook**:
- **Notes tab** (`custom_notes`) with `comment` field labeled "Notes".

Hides standard tabs: `sales_purchases`, `internal_notes`, `contact_addresses`.

---

### `views/res_partner_filter_view.xml`

Inherits `base.view_res_partner_filter`. Adds `<field name="comment" string="Notes"/>` to the Contacts search view, enabling full-text search on the partner's internal notes field.

---

### `views/applicant_views.xml`

**List view** (`view_applicant_list`):
Columns: Full Name, Phone, Mobile, Email, Registrar (`manager_id`), Source (`reference_source`), Expected Join Date, Status (`applicant_state` with badge widget and color decorations: info=interested, warning=needs_to_be_called/no_answer/trial_no_contact, primary=called, success=planned_trial/paid, danger=not_want).

**Kanban view** (`view_applicant_kanban`):
`default_group_by="applicant_state"`. Card displays: name (bold), a warning badge with `no_answer_type_effective` value if state is "No Answer", phone (with phone icon), manager, reference source. Uses QWeb `t-if` conditionals.

**Search view** (`view_applicant_search`):
Searchable fields: name, phone, email, manager.

Filters:
- **Today** — complex domain using OR logic:
  - For `remember` state records: `expected_join_date == today`
  - For all other records: `create_date` is within today OR `expected_join_date == today`
- **This Week** (DEFAULT) — eyni məntiq, cari həftəyə (Bazar ertəsi → Bazar; `context_today() - relativedelta(days=weekday())` … +7 gün) genişləndirilmiş halı
- Individual filter per `applicant_state` (excluding `planned_remember` which has its own menu section)
- Group By: Status, Manager, Source

**Action** (`action_applicants`):
- `view_mode`: kanban, list, form
- Domain: `[('is_applicant', '=', True), ('applicant_state', '!=', 'planned_remember')]`
- Context: `{'default_is_applicant': True, 'search_default_week': 1}` — **default filter artıq "This Week"** ("Today" yan-yana qalır, bir kliklə seçilir)
- Uses explicit view_ids: kanban → `view_applicant_kanban`, list → `view_applicant_list`

**Menu entries:**
- Renames the existing `contacts.menu_contacts` record to "Applicants" (global rename of the Contacts app top menu).
- Adds child menu `menu_applicants_list` ("Applicants") under that parent at sequence 1.

---

### `views/student_views.xml`

**List view** (`view_student_list`):
Columns: Full Name, Phone, Mobile, Email, Registrar, Teacher, Source, Status (`lead_state` badge: info=lesson_not_planned, warning=lesson_planned, success=lesson_complete).

**Kanban view** (`view_student_kanban`):
`default_group_by="lead_state"`. Card: name, phone, manager, teacher, reference source.

**Search view** (`view_student_search`):
Searchable fields: name, phone, email, manager, teacher.
Filters: one per `lead_state`.
Group By: Status, Manager, Teacher, Source.

**Action** (`action_students`):
- `view_mode`: kanban, list, form
- Domain: `[('is_student', '=', True)]`
- Context: `{'default_is_student': True}`
- Uses explicit view_ids: kanban → `view_student_kanban`, list → `view_student_list`

Note: No `<menuitem>` is defined in this file. Students are accessible via the action but have no dedicated top-level menu entry.

---

### `views/waiting_student_views.xml`

**Gözləyən tələbələr** — ödəniş edib, amma hələ qrupu olmayanlar.

**List** (`view_waiting_student_list`): Full Name, Phone, Mobile, Registrar, **Sold Program** (`tl_system_choice`), **Paid** (`tl_payment_amount`, sum), **Expected Start** (`expected_join_date`), **Groups** (`training_group_count`).
Sətir rəngi: qrupu yoxdursa sarı (`decoration-warning`), varsa yaşıl.

**Search** (`view_waiting_student_search`): "Starting This Week" / "Start Date Passed" filtrləri; group by Sold Program / Manager / Expected Start.

**Action** (`action_waiting_students`): domain `[('is_student','=',True), ('is_waiting_student','=',True)]`, view_mode list,form.

**Menu:** `menu_waiting_students` — "Waiting Students", parent `contacts.menu_contacts`, sequence 3.

---

### `views/planned_remember_views.xml`

**List view** (`view_planned_remember_list`):
Columns: Full Name, Phone, Mobile, Email, Manager, Planned Date (`planned_remember_date`), Planned By (`planned_remember_employee_id`).

**Action** (`action_planned_remember`):
- `view_mode`: list, form
- Domain: `[('is_applicant', '=', True), ('applicant_state', '=', 'planned_remember')]`
- Context: `{'default_is_applicant': True, 'default_applicant_state': 'planned_remember'}`

**Menu:** `menu_planned_remember` — "Planned Remember" under `contacts.menu_contacts` at sequence 2.

---

### `views/planned_remember_wizard_view.xml`

**Form view** (`view_planned_remember_wizard_form`) for `res.partner.planned.remember.wizard`:
- `partner_id` — hidden (`invisible="1"`)
- `employee_id` — readonly
- `planned_date` — required

Footer: "Save" button (`action_confirm`, btn-primary) and "Cancel" (btn-secondary, special cancel).

---

## Security

### `security/ir.model.access.csv`

| id | name | model | group | read | write | create | unlink |
|---|---|---|---|---|---|---|---|
| `access_planned_remember_wizard_user` | access_planned_remember_wizard_user | `model_res_partner_planned_remember_wizard` | `base.group_user` | 1 | 1 | 1 | 1 |

Only the wizard transient model requires an explicit access rule. All `res.partner` field additions inherit existing partner access rights from `base` and `contacts`. No custom security groups or record rules are defined in this module.

---

## Important Notes

1. **`trail_lesson` is a hard dependency**: All `tl_*` related fields, `trail.lesson`, and its config models (`trail.lesson.config.company`, `trail.lesson.config.position`, etc.) are defined in the `trail_lesson` module. This module will not install without it.

2. **Multiple `_inherit = 'res.partner'` files**: Python imports them sequentially via `models/__init__.py`. Odoo merges all extensions at registry time. There is no naming conflict. A commented-out `# from . import ir_ui_menu` line indicates an abandoned file that was removed.

3. **Odoo 18 `invisible`/`readonly`/`required` syntax**: All view attributes use Python expression strings (e.g., `invisible="applicant_state != 'interested' or not is_applicant"`). Domain-list format (`[('field', '=', value)]`) does NOT work in Odoo 18 view attributes.

4. **`action_set_trial_no_contact()` does not set `trial_no_contact` state**: This method sets `applicant_state = 'no_answer'` and `no_answer_type = 'before_trial'`. The `trial_no_contact` selection value exists in the field definition (for legacy records) but no current method assigns it. The `_compute_no_answer_type_effective` method still handles it for backward compatibility.

5. **Applicant → Student promotion via `action_set_paid()`**: Sets `applicant_state = 'paid'`, `is_applicant = False`, `is_student = True` on the same `res.partner` record atomically. The record disappears from the Applicants view (domain excludes non-applicants) and appears in the Students view. The `applicant_state = 'paid'` value persists as a historical marker.

6. **`tl_join_timing` is the only writable `tl_*` field**: All other related fields are `readonly=True`. In the form view, `tl_join_timing` is additionally restricted to be editable only when `applicant_state == 'remember'`. Changing it fires `_onchange_tl_join_timing_remember` which syncs `expected_join_date`.

7. **Non-reactive compute fields**: Both `_compute_trail_lesson_count` and `_compute_trial_lesson_id` use `@api.depends()` (empty tuple). They compute once on form load and do NOT auto-update when `trail.lesson` records change. A form save or page reload is needed to see updated data.

8. **`trial_lesson_id` is `store=False`**: This computed Many2one is not persisted to the database. It cannot be used in domain filters, list views, or group-by operations.

9. **Applicant activity on create**: New applicants automatically get a "call" activity scheduled. The code is defensive — it checks for an existing activity to avoid duplicates, and falls back through multiple activity type lookups if `mail.mail_activity_data_call` is not found.

10. **Guard on `action_set_needs_to_be_called()`**: Raises `UserError` if `trial_teacher_id` is not set. Same guard exists in `action_create_trial_lesson()`. Ensure a trial teacher is always set before progressing an applicant past the `interested` state.

11. **Global menu rename**: `applicant_views.xml` modifies the `contacts.menu_contacts` record directly, renaming it from "Contacts" to "Applicants". This affects the top-level menu label for ALL users in the Contacts app — it is not scoped to this module's context.

12. **No Student menu**: `student_views.xml` defines the action but no `<menuitem>`. Students are accessible only via direct URL to `action_students`. (Sequence 3-ü artıq **Waiting Students** menyusu tutub — Students menyusu əlavə ediləndə başqa sequence seçilməlidir.)
13. **`is_waiting_student` axını:** yalnız sınaq tamamlama wizard-ı qoyur (ödəniş + gec başlama), yalnız `training.student.line` yaradılanda söndürülür. Applicant "Paid" düyməsi (finance wizard-ı) bu bayrağı **qoymur** — o adam dərhal tələbə olur.

13. **Wizard employee requirement**: The `employee_id` field in `res.partner.planned.remember.wizard` defaults to `self.env.user.employee_id` and is marked `required=True`. If the current user has no linked `hr.employee` record, the wizard will open with an empty required field and block the user from saving. All staff who use this wizard must have HR employee records linked to their user accounts.

14. **`planned_remember` records excluded from Applicants action**: `action_applicants` has `applicant_state != 'planned_remember'` in its domain. These records are only visible via the separate "Planned Remember" menu (`action_planned_remember`). This is an intentional separation for workflow clarity.

15. **`tl_complete_notes` source**: This field reflects `trial_lesson_id.complete_notes`, which is typically written by the trial lesson completion wizard in the `trail_lesson` module. It is readonly on the partner form.

16. **`lesson_record` is now a hard dependency**: The Training Groups smart button and Meeting tab reference `training.group` and `lesson.student.line` (from `training_management` / `lesson_record`). The manifest declares `lesson_record` in `depends`, which transitively pulls `training_management`. No circular dependency arises (those modules do not depend back on `contact_customization`). `training_management`'s `is_student` domain stays a runtime-only reference.

17. **Meeting widget is read-only & non-reactive**: `meeting_comments_widget` loads via `orm.call('res.partner','get_meeting_comments',[[id]])` on `onWillStart` only — it does not refresh automatically when comments change elsewhere (reopen the form to refresh). Comments are NOT editable here; they are edited on the lesson record. `meeting_line_ids` exists only as the field the widget attaches to. `training_group_count` uses empty `@api.depends()` (same non-reactive caveat as `trail_lesson_count`).
