# trail_lesson — Module Map

**Odoo 18 | Standalone application | Trial lesson scheduling, assessment, and decision tracking**

Depends: `base`, `mail`, `hr`

> **Calendar inteqrasiyası TAM ÇIXARILIB.** `calendar` asılılığı, `calendar_event_id` sahəsi, calendar view və bütün `calendar.event` yaratma/silmə məntiqi silinib. `action_schedule`/`action_modify` artıq yalnız `mail.activity` yaradır.

---

## File Tree

```
trail_lesson/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv
├── models/
│   ├── __init__.py
│   ├── trail_lesson.py               → TrailLessonQA + TrailLesson main models
│   ├── trail_lesson_config.py        → 5 config lookup models
│   ├── trail_lesson_question.py      → QUESTION BANK + shared SYSTEM/LEVEL/STAGE selections
│   ├── trail_lesson_complete_wizard.py → CompleteWizard + CompleteWizardQA
│   └── trail_lesson_plan_wizard.py   → PlanWizard
├── views/
│   ├── trail_lesson_views.xml        → form, list, search, action, sequence
│   ├── trail_lesson_complete_wizard_views.xml
│   ├── trail_lesson_plan_wizard_views.xml
│   ├── trail_lesson_config_views.xml → list+form+action for all 5 config models
│   ├── trail_lesson_question_views.xml → question bank list/form/search/action
│   └── trail_lesson_menus.xml        → root menu + Trail Lessons + Configurator submenus
└── static/
    └── description/
        └── icon.png
```

---

## Models

### trail.lesson.qa (trail_lesson.py)

Persistent Q&A lines. One lesson → many QA lines.

`_order = 'sequence, id'`

| Field | Type |
|-------|------|
| `lesson_id` | Many2one → trail.lesson (ondelete=cascade, required) |
| `sequence` | Integer (default 10) |
| `question` | Char (required) — "Question (EN)" |
| `answer` | Char — "Student's Answer" |
| `translation` | Char — "Translation (AZ/RU)" |

---

### trail.lesson (trail_lesson.py)

`_inherit = ['mail.thread', 'mail.activity.mixin']` | `_order = 'lesson_datetime desc'`

**Core fields**
| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | auto-seq TL/YYYY/XXXX, readonly, default='New' |
| `state` | Selection | not_planned / planned / completed / missing; tracking=True |
| `teacher_id` | Many2one → hr.employee | required, tracking |
| `student_id` | Many2one → res.partner | required, tracking |
| `lesson_datetime` | Datetime | **required=True**, tracking — sınaq dərsi tarixsiz yaradıla bilməz |
| `video_record` | Binary | attachment=True |
| `video_record_filename` | Char | |
| `video_preview_html` | Html | computed, sanitize=False; renders HTML video player |
| `notes` | Html | |
| `complete_notes` | Text | written from wizard_notes in complete wizard |

**Assessment — Background**
| Field | Type |
|-------|------|
| `lesson_company_id` | Many2one → trail.lesson.config.company |
| `position_id` | Many2one → trail.lesson.config.position |
| `school_id` | Many2one → trail.lesson.config.school (label: **School / Uni**) |
| `gender` | Selection: male/female/other |
| `approximate_age` | Selection: under_18/18_25/26_35/36_45/46_55/over_55 |
| `english_level` | Selection: a1–c2; tracking |
| `qa_ids` | One2many → trail.lesson.qa |

**Assessment — Evaluation**
| Field | Type |
|-------|------|
| `comprehension` | Selection: poor/average/good/excellent |
| `motivation` | Selection: low/medium/high |
| `learning_purpose_id` | Many2one → trail.lesson.config.learning.purpose |
| `previous_courses` | Boolean |
| `course_id` | Many2one → trail.lesson.config.course |
| `for_whom` | Selection: self/child/spouse/other (default=self) |
| `for_whom_note` | Char |

**Assessment — Decision**
| Field | Type | Notes |
|-------|------|-------|
| `decision` | Selection: joining/not_joining/thinking | tracking |
| `thinking_reason` | Selection: price/schedule/family/comparing/other | "Reason for Thinking" |
| `system_choice` | Selection (`SYSTEM_SELECTION`) | Essentials / Forward / Acceleration / **Old Program** / Speaking / Other |
| `system_choice_note` | Char | "System Choice Note" — visible when system_choice == 'other' |
| `lesson_format` | Selection: group/individual | |
| `payment_type` | Selection: full/deposit | (Installment removed) |
| `payment_amount` | Float | digits=(10,2) |
| `join_timing` | Selection: now/1_week/2_weeks/1_month/3_months/later | |
| `expected_join_date` | Date | tracking |

**ORM overrides**
- `create()`: assigns sequence name TL/YYYY/XXXX; uses `mail_create_nolog=True`; if partner is_applicant and not in `paid/not_want/planned_trial/planned_remember` → sets `partner.applicant_state = 'planned_trial'`
- `unlink()`: standart davranış (calendar event silmə məntiqi çıxarılıb — override yoxdur)
- `write()`: when `state` changes (except `missing`), posts chatter note on partner (if is_applicant or is_student): `"Trial Lesson [link]: OldState → NewState"` using `Markup`; `missing` is skipped because `action_missing()` handles partner chatter separately

**`_STATE_LABELS` dict** — used for human-readable state labels in write() chatter:
`{'not_planned': 'Not Planned', 'planned': 'Planned', 'completed': 'Completed', 'missing': 'Missing Lesson'}`

---

### Button methods

| Method | From state | Side effects |
|--------|-----------|--------------|
| `action_schedule()` | not_planned | requires lesson_datetime; creates mail.activity (meeting type, assigned to teacher.user_id); state → planned |
| `action_complete()` | planned | opens `trail.lesson.complete.wizard` (target: new) |
| `action_missing()` | planned | marks activities done; state → missing; if student is_applicant → sets `applicant_state = 'no_answer'` + `no_answer_type = 'before_trial'`; posts chatter note on partner + on lesson |
| `action_modify()` | planned | marks existing activities done; recreates the mail.activity (same logic as action_schedule); state stays planned |
| `action_plan_new_trial()` | any | opens `trail.lesson.plan.wizard` prefilled with `student_id` + `teacher_id` (current lesson's teacher) |

**action_schedule / action_modify mail.activity:**
- type: `mail.mail_activity_data_meeting`
- summary: `"Trial Lesson: {student} / {teacher}"`
- date_deadline: `lesson_datetime.date()`
- activity assigned to: `teacher.user_id` if exists, else `env.uid`
- activity note contains: local-timezone-formatted date string (user's tz or UTC)

---

### trail.lesson.complete.wizard (trail_lesson_complete_wizard.py)

`_name = 'trail.lesson.complete.wizard'` (TransientModel)

Contains mirror fields of trail.lesson assessment + Q&A + decision. Plus:
- `lesson_id` — Many2one → trail.lesson (required, readonly)
- `wizard_notes` — Text (written to `lesson.complete_notes` on confirm)
- `thinking_reason` — Selection: price/schedule/family/comparing/other
- `system_choice` — Selection: shared `SYSTEM_SELECTION` (Essentials / Forward / Acceleration / Old Program / Speaking / Other)
- `qa_level` — Selection (`LEVEL_SELECTION`) — **"Question Level"**: hansı levelin sualları Q&A tabına yüklənsin
- `qa_ids.question_id` — Many2one → `trail.lesson.question` (sətir hansı bank sualından gəlib)
- `system_choice_note` — Char ("System Choice Note"; shown when system_choice == 'other')
- `join_timing` — **required=True** at field level (not just in action_confirm)
- `decision` — **required=True** at field level (also validated in action_confirm)
- `payment_required` — Boolean computed: `decision == 'joining' AND join_timing == 'now'`; store=False

**_TIMING_DAYS map:** now=0, 1_week=7, 2_weeks=14, 1_month=30, 3_months=90

**Onchange `_onchange_join_timing`:** auto-fills `expected_join_date` from today + timing days; clears (False) when 'later'

**Onchange `_onchange_payment_type_full`:** `payment_type == 'full'` → `join_timing = 'now'` + `expected_join_date = bugün`
(çünki Full Payment-də Join Timing view-da gizlədilib, amma sahə required-dir)

**Question Bank inteqrasiyası:**
- `_load_bank_questions()` — `trail.lesson.question.fetch_questions('trial', level=qa_level, system=system_choice)` ilə `qa_ids`-i **tam əvəz edir** ((5,0,0) + create-lər)
- `_onchange_qa_level` — level seçiləndə avtomatik yükləyir
- `_onchange_english_level_qa` — `english_level` seçiləndə `qa_level` boşdursa onu doldurub yükləyir
- `action_load_questions()` — Q&A tabındakı **"Reload Questions"** düyməsi (confirm dialoqu ilə); wizardı eyni `res_id` ilə yenidən açır

**action_confirm() logic:**
1. Validates lesson is still 'planned'
2. Validates `decision` is set
3. If `decision == 'joining' AND join_timing == 'now'`: validates `payment_type` (full/deposit) and `payment_amount > 0`
4. Writes all assessment fields back to `lesson` (including `thinking_reason`, `system_choice`, `system_choice_note`, `wizard_notes → complete_notes`)
5. Replaces `lesson.qa_ids` with wizard qa lines (unlink all, create new)
6. Closes all lesson activities (`activities.action_done()`)
7. Sets `lesson.state = 'completed'`
8. Returns `{'type': 'ir.actions.act_window_close'}`

**Partner state transitions:**
- `joining + now` → partner: `is_student=True, is_applicant=False, expected_join_date` set; if partner.is_applicant: also `applicant_state='paid'` + `partner.activity_ids.action_done()`
- `joining (any other timing) OR thinking` → partner: `expected_join_date` set; if is_applicant: `applicant_state='remember'`
- `not_joining` → only if `expected_join_date` provided: partner `expected_join_date` set (no state change)

---

### trail.lesson.complete.wizard.qa (trail_lesson_complete_wizard.py)

`_name = 'trail.lesson.complete.wizard.qa'` (TransientModel)

`_order = 'sequence, id'`

Mirror of `trail.lesson.qa`. Fields: wizard_id (Many2one → complete wizard, ondelete=cascade, required), sequence (Integer, default 10), question (Char, required), answer (Char), translation (Char).

---

### trail.lesson.plan.wizard (trail_lesson_plan_wizard.py)

`_name = 'trail.lesson.plan.wizard'` (TransientModel)

| Field | Type |
|-------|------|
| `student_id` | Many2one → res.partner (required) |
| `teacher_id` | Many2one → hr.employee (required) |
| `lesson_datetime` | Datetime (required) |
| `lesson_id` | Many2one → trail.lesson (readonly) — modify mode |

**action_confirm():**
- **Modify mode** (`lesson_id` set): writes new teacher/datetime + resets state to 'not_planned', calls `action_schedule()`, returns `act_window_close`
- **Create mode** (`lesson_id` not set): creates new trail.lesson (not_planned, no automatic scheduling), opens its form (`target: current`)

> Note: In create mode the new lesson is created in `not_planned` state. The teacher must click "Schedule Trial" on the lesson form to schedule it.

---

### Config models (trail_lesson_config.py)

All have `name` (Char, required) + `active` (Boolean, default True) + `_order = 'name'`

| Model | _name | name field label |
|-------|-------|-----------------|
| TrailLessonConfigCompany | trail.lesson.config.company | 'Company Name' |
| TrailLessonConfigPosition | trail.lesson.config.position | 'Position / Title' |
| TrailLessonConfigCourse | trail.lesson.config.course | 'Course Name' |
| TrailLessonConfigSchool | trail.lesson.config.school | 'School Name' |
| TrailLessonConfigLearningPurpose | trail.lesson.config.learning.purpose | 'Learning Purpose' |

---

### trail.lesson.question — QUESTION BANK (trail_lesson_question.py)

**Sınaq dərsinin VƏ imtahanların sualları bir cədvəldə.** `stage` onları ayırır.

`_order = 'stage, exam_number, sequence, id'`

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char (required) | **Title** — sualın başlığı |
| `question` | Text (required) | sualın özü |
| `translation` | Char | AZ/RU tərcümə |
| `stage` | Selection: `trial` / `exam` | hansı etapa aiddir |
| `exam_number` | Integer | yalnız `exam` üçün: 1 = 5-ci dərsdən sonra, 2 = 10-cu… **0 = bütün imtahanlarda** |
| `level` | Selection (`LEVEL_SELECTION`) | **boş = bütün levellər** |
| `system_choice` | Selection (`SYSTEM_SELECTION`) | **boş = bütün proqramlar** |
| `note` | Text | "Details / Expected Answer" — müəllim üçün daxili qeyd |
| `sequence` | Integer (default 10) | |
| `active` | Boolean (default True) | arxivləmə = sual daha çəkilmir |

**Metodlar:**
- `_display_question()` — sətirə yazılacaq mətn (`question`, yoxsa `name`)
- `fetch_questions(stage, level=None, exam_number=None, system=None)` (`.model`) — uyğun **aktiv** sualları qaytarır. Boş `level`/`system_choice`/`exam_number` olan suallar **həmişə** nəticəyə düşür ("universal" suallar).

**Paylaşılan seçimlər (bu fayldadır, hər yerdən import olunur):**
`SYSTEM_SELECTION` (6 dəyər), `LEVEL_SELECTION` (a1–c2), `STAGE_SELECTION` (trial/exam).
İstifadəçilər: `trail.lesson`, `trail.lesson.complete.wizard`, `training.group` (training_exam →
`from odoo.addons.trail_lesson.models.trail_lesson_question import SYSTEM_SELECTION`).

---

## Views

### trail_lesson_views.xml

**trail_lesson_form_view** — Header buttons:
- Save (special=save, class=btn-secondary, icon=fa-floppy-o, invisible when state == 'planned')
- Modify (btn-warning, icon=fa-pencil, invisible when state != 'planned') → action_modify
- Schedule Trial (btn-primary, invisible when state != 'not_planned') → action_schedule
- Complete Trial (btn-success, invisible when state != 'planned') → action_complete
- Missing Lesson (btn-danger, icon=fa-times-circle, invisible when state != 'planned', has confirm dialog) → action_missing
- Plan New Trial (btn-secondary, icon=fa-calendar-plus-o, always visible) → action_plan_new_trial
- statusbar: statusbar_visible="not_planned,planned,completed,missing"

Form body:
- `student_id` is `readonly="state != 'not_planned'"` (cannot change student after scheduling)

Tabs (notebook):
- **Notes** — always visible
- **Assessment** — invisible when state != 'completed'; contains Student Background group + Evaluation group + Q&A separator + qa_ids list
- **Decision** — invisible when state != 'completed'; contains decision (radio), thinking_reason (invisible unless decision=thinking), lesson_format, join_timing, expected_join_date, payment group (invisible unless joining), system_choice (radio)
- **Record Preview** — invisible when state != 'completed'; shows video_preview_html (readonly html widget)

**trail_lesson_tree_view** — Row decorations: success=completed, info=planned, danger=missing, muted=not_planned. Columns: name, teacher_id, student_id, lesson_datetime, english_level, decision, state (badge widget with per-state colors)

**trail_lesson_search_view** — search fields: name, teacher_id, student_id; filters: Not Planned / Planned / Completed / Missing Lesson; group by: Teacher / Status / Decision

**trail_lesson_action** (id: `trail_lesson.trail_lesson_action`) — view_mode: list,form

**seq_trail_lesson** — code: `trail.lesson`, prefix: `TL/%(year)s/`, padding: 4, number_next: 1, number_increment: 1

---

### trail_lesson_complete_wizard_views.xml

Single form view (`view_trail_lesson_complete_wizard_form`). Four tabs inside a notebook:
1. **Student Background** — Personal group (gender, approximate_age, for_whom, for_whom_note) + Professional group (lesson_company_id, position_id, school_id, english_level)
2. **Q&A Session** — üstdə `qa_level` seçimi + **"Reload Questions"** düyməsi (`action_load_questions`, confirm ilə); altında editable list (sequence handle, question, answer, translation; `question_id` column_invisible). Suallar Question Bank-dan gəlir, sətirlər burada sərbəst redaktə/əlavə/silinə bilər
3. **Assessment** — Evaluation group (comprehension, motivation, learning_purpose_id) + Background group (previous_courses, course_id)
4. **Decision** — Outcome group (decision required, thinking_reason, lesson_format, join_timing + expected_join_date on same row — **`payment_type == 'full'` olanda Join Timing sətri tam gizlənir**) + Payment group (payment_type/amount, invisible unless joining) + System Choosing group (system_choice radio, system_choice_note when other) + alert-warning banner (shown when thinking or joining-later) + Additional Notes (wizard_notes)

Footer: "Complete Lesson" btn-primary (hotkey v) + Cancel btn-secondary (special=cancel)

---

### trail_lesson_plan_wizard_views.xml

Single form view (`view_trail_lesson_plan_wizard_form`). Simple group: student_id, teacher_id, lesson_datetime. Footer: "Create & Open" btn-primary (hotkey v) + Cancel.

---

### trail_lesson_config_views.xml

For each of the 5 config models: editable list view + simple form view + act_window action. The `active` field is `optional="hide"` in all list views.

---

### trail_lesson_question_views.xml

Question Bank üçün: editable list (title, question, translation, stage, exam_number, level, system_choice, active toggle) + form (Where is it used? / Content / Details) + search (Trial / Exam / Archived filtrləri, Stage-Exam#-Level-System group by) + `action_trail_lesson_question` (default `search_default_group_by_stage`).

---

### trail_lesson_menus.xml

- Root: `menu_trail_lesson_root` — "Trail Lesson", sequence=50, uses icon.png
- Child: `menu_trail_lesson_main` — "Trail Lessons", sequence=10, action=trail_lesson_action
- Child: `menu_trail_lesson_config` — "Configurator", sequence=90 (no action, parent for submenu)
  - **Question Bank** (seq=5) → `action_trail_lesson_question`
  - Companies (seq=10)
  - Positions / Titles (seq=20)
  - Courses (seq=30)
  - Schools (seq=40)
  - Learning Purposes (seq=50)

---

## Security

`security/ir.model.access.csv`:

| Model | read | write | create | unlink |
|-------|------|-------|--------|--------|
| trail.lesson | 0 | 0 | 0 | 0 |
| trail.lesson.qa | 1 | 1 | 1 | 1 |
| trail.lesson.complete.wizard | 1 | 1 | 1 | 1 |
| trail.lesson.complete.wizard.qa | 1 | 1 | 1 | 1 |
| trail.lesson.plan.wizard | 1 | 1 | 1 | 1 |
| trail.lesson.config.company | 1 | 1 | 1 | 1 |
| trail.lesson.config.position | 1 | 1 | 1 | 1 |
| trail.lesson.config.course | 1 | 1 | 1 | 1 |
| trail.lesson.config.school | 1 | 1 | 1 | 1 |
| trail.lesson.config.learning.purpose | 1 | 1 | 1 | 1 |
| trail.lesson.question | 1 | 1 | 1 | 1 |

All rows use `base.group_system`.

⚠️ `trail.lesson` main model has zero permissions in CSV — access must come from another rule or group not visible here (e.g., a record rule or group defined in another module).

---

## State Flow

```
not_planned
    └─ action_schedule() ──→ planned
           ├─ action_complete() → [CompleteWizard] ──→ completed
           │       └─ decision logic updates res.partner
           ├─ action_missing() ──────────────────────→ missing
           │       └─ partner.applicant_state = 'no_answer'
           │       └─ partner.no_answer_type = 'before_trial'
           └─ action_modify() ──────────────────────→ planned (recreates activity)

[any state]
    └─ action_plan_new_trial() → [PlanWizard]
           ├─ Modify mode (lesson_id set): resets→not_planned, action_schedule() → planned
           └─ Create mode: new lesson (not_planned) → open form
```

---

## Cross-module Impact on res.partner

| Trail Lesson Event | Effect on res.partner |
|-------------------|----------------------|
| `trail.lesson.create()` | if partner is_applicant and state not in (paid/not_want/planned_trial/planned_remember) → `applicant_state = 'planned_trial'` |
| `action_missing()` | `applicant_state = 'no_answer'`, `no_answer_type = 'before_trial'` (if is_applicant) + chatter note on partner |
| Complete: joining + now | `is_applicant=False`, `is_student=True`, `expected_join_date` set; if was_applicant: `applicant_state='paid'` + all partner activities done |
| Complete: joining(later) or thinking | `expected_join_date` set; if is_applicant: `applicant_state = 'remember'` |
| Complete: not_joining | only `expected_join_date` set if provided (no state change) |
| `write()` any state change except missing | chatter note on partner (if is_applicant or is_student) |

---

## Important Notes

- `system_choice` has 6 values, defined ONCE in `trail_lesson_question.py` as `SYSTEM_SELECTION` and imported by `trail.lesson`, the complete wizard, the question bank and `training.group` (training_exam):
  `system_1` = **Essentials Program**, `system_2` = **Forward Program**, `system_3` = **Acceleration Program**, `system_4` = **Old Program**, `speaking` = Speaking, `other` = Other.
  ⚠️ DB keys stay `system_1..3` (köhnə qeydlər qorunur) — yalnız etiketlər dəyişib.
- `system_choice_note` (Char) exists on both `trail.lesson` and the complete wizard — it is shown/visible only when `system_choice == 'other'`
- `join_timing` is `required=True` at field level in the complete wizard (not just validated in action_confirm) — buna görə Full Payment-də `_onchange_payment_type_full` onu avtomatik `now` edir
- `lesson_datetime` **required=True** — tarixsiz sınaq dərsi yaradıla bilməz (`contact_customization.action_create_trial_lesson` də öz UserError-u ilə qabaqcadan xəbərdarlıq edir)
- Question Bank sətirləri wizarda **kopyalanır** (snapshot) — wizardda sualı dəyişmək bankdakı sualı dəyişmir
- `action_missing()` marks activities as done (`action_done()`) — it does not delete them
- `action_modify()` also marks existing activities as done before recreating — it does not delete them
- `action_missing()` sets `applicant_state = 'no_answer'` (NOT `trial_no_contact`) and also sets `no_answer_type = 'before_trial'`
- Chatter messages use `markupsafe.Markup` to render HTML correctly in Odoo 18
- `write()` chatter fires for all state changes EXCEPT `missing` — because `action_missing()` posts manually to avoid double messages
- `action_schedule()` and `action_modify()` create only a `mail.activity` (no calendar event); the activity is assigned to `teacher.user_id` (fallback: `env.uid`)
- The complete wizard's `action_confirm()` sets `applicant_state='remember'` (basic remember, not `planned_remember`) for joining-later and thinking decisions
- `wizard_notes` in the wizard is written to `complete_notes` on the lesson — permanent completion notes on the lesson record
- `trail.lesson` main model has 0 permissions in CSV — investigate before adding new access rules
- The `__init__.py` has a commented-out import: `# from . import trail_lesson_extension` — placeholder for future extension
