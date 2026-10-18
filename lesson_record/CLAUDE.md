# Odoo 18 | Standalone Application | Lesson Record — Attendance & Homework

> **Calendar inteqrasiyası TAM ÇIXARILIB.** `calendar_event_id`, `calendar_needs_update` sahələri, `_get_event_datetimes`/`_build_event_*`/`_create_calendar_event_auto`/`_sync_lesson_calendar` helper-ləri, `action_create_lesson_calendar`/`action_modify_lesson_calendar` düymələri, calendar üçün xüsusi `create`/`write`/`unlink` override-ları və calendar view elementləri silinib. `calendar` heç vaxt manifest `depends`-də olmayıb.

**Module:** `lesson_record`
**Version:** 18.0.1.0.0
**Author:** Majidov
**License:** LGPL-3

**Depends:** `base`, `training_management`

---

## File Tree

```
lesson_record/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv         → CRUD access for all 3 models (base.group_user)
├── data/
│   ├── sequence.xml                → ir.sequence (LSN/0001 format); DEFINED but not called in create()
│   └── lesson_cron.xml             → scheduled action: every 15 min, notifies incomplete lessons
├── models/
│   ├── __init__.py
│   ├── lesson_record.py            → main model
│   ├── lesson_student_line.py      → per-student attendance + homework
│   └── lesson_record_cron.py       → cron notification logic (_inherit 'lesson.record')
├── wizards/
│   ├── __init__.py
│   └── lesson_homework_wizard.py   → homework file management popup (TransientModel)
└── views/
    ├── lesson_record_views.xml         → list, form, search views + window action
    ├── lesson_menu.xml                 → top-level root menu + "Lessons" submenu
    └── lesson_homework_wizard_views.xml → wizard popup form
```

---

## Models

### lesson.record (`models/lesson_record.py`)

`_inherit = ['mail.thread', 'mail.activity.mixin']`
`_order = 'lesson_date desc, lesson_number desc'`

#### Fields

| Field | Type | Notes |
|---|---|---|
| `name` | Char | Auto-built in `create()` as `"{group.name} - Lesson {lesson_number}"`. `readonly=True`, `default='New'`, `copy=False`. The sequence (LSN/XXXX) is **not** used for name generation. |
| `lesson_number` | Integer | `readonly=True`, `default=0`, `tracking=True` |
| `group_id` | Many2one → `training.group` | required, `ondelete='cascade'` |
| `teacher_id` | Many2one → `hr.employee` | related from `group_id.teacher_id`, `store=True`, `readonly=True` — cannot be changed directly |
| `lesson_date` | Date | required, `tracking=True` |
| `start_time` | Float | required, `tracking=True` — stored as 24h float (e.g. 9.5 = 09:30) |
| `end_time` | Float | required, `tracking=True` — stored as 24h float |
| `lesson_time_display` | Char | computed, `store=True` — formatted as `"09:00 - 11:00"` |
| `state` | Selection | `scheduled` ("Lesson Not Held") / `completed` ("Lesson Held"); `default='scheduled'`, `tracking=True` |
| `student_line_ids` | One2many → `lesson.student.line` | via `lesson_id` |
| `teacher_comment` | Text | |
| `student_count` | Integer | computed, `store=True` — `len(student_line_ids)` |
| `present_count` | Integer | computed, `store=True` — lines where `attendance='present'` |
| `absent_count` | Integer | computed, `store=True` — lines where `attendance='absent'` |
| `source` | Selection | `group` / `manual`; `default='manual'`, `readonly=True`, `copy=False` |

#### Computed Field Methods

| Method | Depends | Logic |
|---|---|---|
| `_compute_lesson_time_display` | `start_time`, `end_time` | Converts float hours to `"HH:MM - HH:MM"` string |
| `_compute_student_count` | `student_line_ids` | `len(student_line_ids)` |
| `_compute_attendance_count` | `student_line_ids.attendance` | Counts present vs absent lines |

#### ORM Overrides

**`create(vals_list)`** (`@api.model_create_multi`):
- For each record where `name == 'New'`, builds name as `"{group.name} - Lesson {lesson_number}"`
- NOTE: Does NOT call `env['ir.sequence'].next_by_code('lesson.record')` — the sequence exists in `data/sequence.xml` but is not used
- Returns `super().create(vals_list)` (calendar auto-create məntiqi tamamilə silinib; `write`/`unlink` override-ları artıq yoxdur — standart ORM davranışı)

#### Button Action Methods

| Method | Visible When | Effect |
|---|---|---|
| `action_complete_lesson()` | `id` is set AND `state == 'scheduled'` (oe_highlight in header) | Sets `state = 'completed'` for all records in the set |

#### Constraint & Utility

- `@api.constrains('start_time', 'end_time')` — `_check_time_validity()`: raises `ValidationError` if `start_time >= end_time`
- `_needaction_domain_get()`: returns `[('state', '=', 'scheduled')]` — used by Odoo to show a badge counter on the menu item for records needing action

---

### lesson.student.line (`models/lesson_student_line.py`)

`_rec_name = 'student_id'`

#### Fields

| Field | Type | Notes |
|---|---|---|
| `lesson_id` | Many2one → `lesson.record` | required, `ondelete='cascade'` |
| `student_id` | Many2one → `res.partner` | required, `domain=[('is_company', '=', False)]` |
| `phone` | Char | related from `student_id.phone`, readonly |
| `mobile` | Char | related from `student_id.mobile`, readonly |
| `attendance` | Selection | `present` / `absent`; `default='present'`, required |
| `comment` | Text | per-student lesson comment |
| `homework_attachment_ids` | Many2many → `ir.attachment` | relation table: `lesson_student_line_attachment_rel` (cols: `student_line_id`, `attachment_id`) |
| `homework_count` | Integer | computed (not stored) from `len(homework_attachment_ids)` |

#### Methods

**`_compute_homework_count()`** — `@api.depends('homework_attachment_ids')`, not stored.

**`action_open_homework_wizard()`** — Returns `ir.actions.act_window` opening `lesson.homework.wizard` in `target: 'new'` dialog, passing `default_student_line_id` in context. Called from the "Homework" button in the student line list on the lesson form.

> **Qeyd:** `_sync_lesson_calendar()` helper-i və onu çağıran `create`/`write`/`unlink` override-ları TAM SİLİNİB. Bu model artıq yalnız `_compute_homework_count` və `action_open_homework_wizard` saxlayır — calendar sinxronizasiyası yoxdur.

#### SQL Constraint

`UNIQUE(lesson_id, student_id)` — "A student cannot be added to the same lesson twice!"

---

### lesson.homework.wizard (`wizards/lesson_homework_wizard.py`)

`TransientModel` | `_name = 'lesson.homework.wizard'`

#### Fields

| Field | Type | Notes |
|---|---|---|
| `student_line_id` | Many2one → `lesson.student.line` | required |
| `student_id` | Many2one → `res.partner` | related from `student_line_id.student_id`, readonly |
| `lesson_id` | Many2one → `lesson.record` | related from `student_line_id.lesson_id`, readonly |
| `attachment_ids` | Many2many → `ir.attachment` | relation table: `lesson_homework_wizard_attachment_rel` (cols: `wizard_id`, `attachment_id`) |

#### Methods

**`default_get(fields_list)`** (`@api.model`):
- Reads `default_student_line_id` from context
- Pre-populates `attachment_ids` with the student line's current `homework_attachment_ids` using `(6, 0, [...ids...])`

**`action_save()`**:
- Writes `self.attachment_ids` directly to `self.student_line_id.homework_attachment_ids`
- Returns `{'type': 'ir.actions.act_window_close'}`

**`action_save_and_stay()`**:
- Same write as `action_save()`
- Returns `ir.actions.act_window` reopening the same wizard (`res_id=self.id`, `target: 'new'`)
- NOTE: This method exists in the model but is **not exposed** in the wizard view XML (only "Save & Close" and "Discard" buttons are in the view)

---

### LessonRecordCron (`models/lesson_record_cron.py`)

`_inherit = 'lesson.record'` — extends `lesson.record` with cron logic (no new fields).

#### `_cron_notify_incomplete_lessons()` (`@api.model`)

Called by the scheduled action every 15 minutes. Logic:

1. Gets user's local time: `datetime.now(pytz.timezone(env.user.tz or 'UTC'))`
2. Computes `current_time_float = hour + minute / 60.0` and `today = now_local.date()`
3. Searches `lesson.record` for:
   - `lesson_date == today` (in user's local date)
   - `end_time < current_time_float` (lesson end time already passed)
   - `state == 'scheduled'` (not yet marked complete)
4. Logs found lesson IDs
5. Calls `_send_incomplete_notification()` on each found lesson

#### `_send_incomplete_notification()`

1. Checks `self.teacher_id` — skips if no teacher
2. Resolves partner: `teacher.user_id.partner_id` (if user exists) or `teacher.address_id`; skips with warning if no partner
3. Gets `admin_partner = env.ref('base.user_admin').partner_id`
4. Builds an HTML `@mention` markup linking to the teacher's partner record
5. Builds body message: `"⚠️ @{teacher} {lesson.name} dərsi {time} vaxtında bitməli idi, lakin hələ tamamlanmayıb. Zəhmət olmasa statusu yeniləyin."`
6. Posts to **`mail.channel_admin`** (Administrators channel) via `channel.message_post(...)` with `partner_ids=partner.ids` — this triggers a push notification to the teacher
7. Posts the same message to the **lesson's own chatter** via `self.sudo().message_post(...)` — visible on the lesson record
8. Logs info: lesson name + teacher partner name

---

## Sequence (`data/sequence.xml`)

Defined with `noupdate="1"`:

| Attribute | Value |
|---|---|
| `code` | `lesson.record` |
| `prefix` | `LSN/` |
| `padding` | 4 |
| `number_next` | 1 |
| `number_increment` | 1 |

**Important:** The sequence is defined but **never called** in `lesson_record.py`. The `name` field is built manually in `create()` as `"{group.name} - Lesson {lesson_number}"`. The XML comment says "if needed in future" — the sequence is reserved for future use only.

---

## Cron Job (`data/lesson_cron.xml`)

| Attribute | Value |
|---|---|
| `id` | `ir_cron_notify_incomplete_lessons` |
| `name` | `Lesson: Notify Incomplete Lessons` |
| `model` | `lesson.record` |
| `code` | `model._cron_notify_incomplete_lessons()` |
| `interval_number` | 15 |
| `interval_type` | minutes |
| `active` | True |

The cron fires every 15 minutes and notifies teachers about lessons that should have ended (by `end_time`) but are still in `scheduled` state. Timezone-aware: uses the running user's timezone.

---

## Wizards

### lesson.homework.wizard

Popup (dialog) for managing homework file uploads per student per lesson.

- Opened via the "Homework" button (folder icon) in the student line list on the lesson form
- Displays student name and lesson name (both readonly)
- Shows a `many2many_binary` widget for file uploads
- "Save & Close" button calls `action_save()` and closes
- "Discard" button cancels without saving
- On open: pre-loads existing files from `lesson.student.line.homework_attachment_ids` via `default_get()`

---

## Views

### lesson_record_views.xml

**List view** (`view_lesson_record_tree`): shows name, lesson_number, group, teacher, date, time display, present/absent counts, state badge (warning=scheduled, success=completed).

**Form view** (`view_lesson_record_form`):
- Header: "Complete Lesson" button (oe_highlight, visible only when record is saved and state='scheduled'), statusbar (scheduled → completed). (Calendar banner və "Modify Lesson" düyməsi silinib.)
- Main sheet: group/teacher/lesson_number on left, date/start_time/end_time/lesson_time_display on right
- Student counts (total, present, absent)
- Notebook tabs: **Students** (editable inline list with attendance color decoration, comment, homework count, homework wizard button; `create=0`, `delete=0`) and **Teacher Comment** (free text)
- Chatter (`<chatter/>`)

**Search view** (`view_lesson_record_search`): search by name, group, teacher, date. Filters: Scheduled, Completed, Today. Group by: Group, Teacher, Date, Status.

**Window action** (`action_lesson_record`): `list,form`, defaults to `filter_scheduled` active.

### lesson_menu.xml

- `menu_lesson_root`: top-level root menu item named **"Lesson Records"**, `sequence=15`, uses `web_icon` (standalone app icon — not nested under Training Management)
- `menu_lesson_records`: submenu item "Lessons" pointing to `action_lesson_record`

### lesson_homework_wizard_views.xml

Form-only view for `lesson.homework.wizard`. Footer: "Save & Close" (btn-primary, calls `action_save`) and "Discard" (btn-secondary, `special="cancel"`).

---

## Security (`security/ir.model.access.csv`)

| ID | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|
| `access_lesson_record_user` | `lesson.record` | `base.group_user` | 1 | 1 | 1 | 1 |
| `access_lesson_student_line_user` | `lesson.student.line` | `base.group_user` | 1 | 1 | 1 | 1 |
| `access_lesson_homework_wizard_user` | `lesson.homework.wizard` | `base.group_user` | 1 | 1 | 1 | 1 |

All three models grant full CRUD to all internal users (`base.group_user`). No role separation.

---

## Lesson Creation Flow

```
training.group.action_start()
  └─ lesson.record.create()            ← name = "{group} - Lesson {n}"
        └─ lesson.student.line.create()  ← Training Group tələbələri ayrıca yazır
```

> Calendar event yaratma/sinxronizasiya/silmə axını TAM ÇIXARILIB. `create`/`write`/`unlink` standart ORM davranışı ilə işləyir.

---

## Important Notes

1. **Sequence is declared but unused.** `data/sequence.xml` registers `lesson.record` with prefix `LSN/`, but `lesson_record.py:create()` never calls `env['ir.sequence'].next_by_code('lesson.record')`. Names are built as `"{group.name} - Lesson {lesson_number}"`.

2. **`teacher_id` is read-only (related field).** Changing the teacher requires editing the linked `training.group` record.

3. **Cron is timezone-aware.** `_cron_notify_incomplete_lessons()` uses the running Odoo user's timezone (not UTC) to determine the current time and today's date, ensuring lesson `end_time` comparison is meaningful.

4. **Calendar inteqrasiyası TAM ÇIXARILIB.** Bütün `calendar.event` yaratma/yeniləmə/silmə, sinxronizasiya helper-ləri, `calendar_event_id`/`calendar_needs_update` sahələri, "Modify Lesson" düyməsi, banner və "Needs Calendar Update" filtri silinib. `write`/`unlink` override-ları artıq yoxdur — standart ORM davranışı.

5. **`action_save_and_stay()` is not in the wizard view.** The method exists in `lesson_homework_wizard.py` but the wizard form only exposes "Save & Close" and "Discard".

6. **Menu is top-level (standalone app).** `menu_lesson_root` has a `web_icon` attribute and no `parent`, making it a standalone app in the Odoo home menu, not nested under Training Management.

7. **`_needaction_domain_get()`** returns `[('state', '=', 'scheduled')]`, enabling Odoo to display a badge counter on the menu item showing the number of unresolved (scheduled) lessons.

8. **`student_line_ids` in form is non-editable for add/delete.** The inline list has `create=0` and `delete=0` — students are managed by the Training Group, not directly on the lesson form. Only attendance and comments can be edited inline.
