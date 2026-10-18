# Odoo 18 | Standalone Application | Training Group Scheduling and Student Management

**Module:** `training_management`
**Version:** 18.0.1.0.0
**Category:** Education
**Author/Tag:** Majidov

Depends: `base`, `hr`, `contacts`

---

## File Tree

```
training_management/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv              → full CRUD for base.group_user on all 4 models
├── data/
│   └── sequence.xml                     → prefix TRG/, padding 4 (declared but NOT used in create())
├── models/
│   ├── __init__.py
│   ├── training_group.py                → main model (TrainingGroup)
│   ├── training_schedule_line.py        → schedule slots (day + time)
│   ├── training_student_line.py         → enrolled students per group
│   └── training_group_delete_wizard.py  → confirm-delete popup (TransientModel)
└── views/
    ├── training_group_views.xml              → list, form, search views + window action + delete wizard action binding
    ├── training_group_delete_wizard_views.xml → confirm-delete popup form
    └── training_menu.xml                     → root "Training" menu + "Training Groups" child menu
```

---

## Models

### training.group (training_group.py)

`_name = 'training.group'`
`_order = 'name desc'`

**Core fields**

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | required, copy=False; entered manually — no auto-sequence despite sequence.xml |
| `lesson_count` | Integer | required, **default=20**; total lessons for the entire group |
| `teacher_id` | Many2one → `hr.employee` | required |
| `training_start_date` | Date | required=False, default=`fields.Date.context_today` |
| `start_day_of_week` | Char | computed from `training_start_date`, store=True, readonly; e.g. "Monday" |
| `state` | Selection | `pending`/`in_progress`/`done`; default=`pending`, required, tracking=True |
| `schedule_line_ids` | One2many → `training.schedule.line` | schedule slots |
| `student_line_ids` | One2many → `training.student.line` | enrolled students |
| `student_count` | Integer | compute from `len(student_line_ids)`, store=True |

**state display labels:**
- `pending` → "Waiting"
- `in_progress` → "Started"
- `done` → "Completed"

---

**Computed fields**

- `_compute_student_count()`: `@api.depends('student_line_ids')` — counts lines.
- `_compute_start_day_of_week()`: `@api.depends('training_start_date')` — maps Python weekday number (0=Monday…6=Sunday) to English name string.

---

**`default_get()` override**

Auto-fills `schedule_line_ids` with 7 slots (Monday through Sunday, `start_time=9.0`, `end_time=10.0`) as convenience defaults when creating a new group.

---

**`create()` override**

```python
@api.model_create_multi
def create(self, vals_list):
    return super().create(vals_list)
```
Passes through to super — no sequence assignment. The `name` field must be typed manually by the user.

---

**Onchange / Constraints**

- `_onchange_lesson_count()`: when the group's `lesson_count` changes, syncs the new value to all `student_line_ids` whose `lesson_count` still equals the group's previous value (`self._origin.lesson_count`). Students whose count was already individually customized (differs from the original group value) are left unchanged.
- `_check_lesson_count()` (`@api.constrains`): raises `ValidationError` if `lesson_count < 1`.

---

**`action_start()`** — transitions `pending → in_progress`

1. Validates that `schedule_line_ids` and `student_line_ids` both exist.
2. Sorts schedule lines by `(day_of_week, start_time)` using a `day_order` dict (`monday=0 … sunday=6`).
3. Iterates `lesson_num` from 1 to `lesson_count` (group-level):
   - `schedule_index = (lesson_num - 1) % len(schedules)` — cycles through schedule slots.
   - **Lesson 1:** Finds the next matching weekday on or after `training_start_date`. If the target weekday is `>= start_weekday`, adds `(target - start)` days; otherwise adds `(7 - start + target)` days.
   - **Lesson N > 1:** Advances from the previous `lesson_date` by the day-difference between consecutive schedule slots (also wraps by 7 if next slot's weekday <= previous slot's weekday).
4. Creates one `lesson.record` per lesson number with `group_id`, `lesson_date`, `start_time`, `end_time`, `lesson_number`.
5. Creates one `lesson.student.line` for every student in `student_line_ids` for every lesson record.
6. Sets `state = 'in_progress'`.
7. Returns `True`.

---

**`action_modify()`** — adjusts lessons when student `lesson_count` differs from actual assigned lessons (state must be `in_progress`)

For each `student_line` in `student_line_ids`:

1. Fetches all `lesson.record` for this group (ordered by date/time).
2. Counts how many `lesson.student.line` records exist for this student.
3. If `current_count >= required` → skips.
4. Otherwise, `deficit = required - current_count`.

**STEP 1 — Fill existing future lessons:**
- Finds future lessons (`lesson_date >= today`) where this student has no `lesson.student.line`.
- Adds the student to those lessons until `deficit == 0`.

**STEP 2 — Create new lesson records (if deficit remains):**
- Re-fetches all lessons (another student's loop may have added records).
- Determines `last_schedule_index = (total_existing - 1) % schedule_count`.
- Loops while `deficit > 0`:
  - Computes `next_schedule_index = (last_schedule_index + 1) % schedule_count`.
  - Calls `_get_next_lesson_date()` to compute the next date.
  - Re-fetches fresh lessons to check if a lesson at that exact date+start_time already exists (created for another student in the same loop):
    - **Slot exists:** adds the student only if not already assigned.
    - **Slot does not exist:** creates a brand-new `lesson.record` and adds only the deficit student (other students are NOT automatically added).
  - Decrements `deficit`.

Returns `True`.

---

**`_get_next_lesson_date(current_date, last_schedule_index, next_schedule_index, schedules, day_order)`**

Helper: computes the date of the next lesson. If `curr_weekday > prev_weekday`: `days_to_add = curr - prev`. Otherwise: `days_to_add = 7 - prev + curr`. Returns `current_date + timedelta(days=days_to_add)`.

---

**`unlink()`**

```python
def unlink(self):
    lesson_records = self.env['lesson.record'].search([('group_id', 'in', self.ids)])
    lesson_records.unlink()
    return super().unlink()
```

Always searches and deletes all linked `lesson.record` entries first, then calls `super().unlink()`. There is **no context guard** — deletion of lesson.records always happens unconditionally.

> Note: The delete wizard (`action_confirm_delete`) also deletes lesson.records before calling `group.unlink()`. This means lesson.record deletion happens twice — but since the wizard already unlinked them, the second `search()` in `unlink()` returns an empty recordset (harmless double-call, not a bug).

---

### training.schedule.line (training_schedule_line.py)

`_name = 'training.schedule.line'`
`_order = 'day_of_week, start_time'`

| Field | Type | Notes |
|-------|------|-------|
| `group_id` | Many2one → `training.group` | required, ondelete=cascade |
| `day_of_week` | Selection | `monday`…`sunday` (7 choices), required |
| `start_time` | Float | 24-hour format (9.0 = 09:00, 14.5 = 14:30), required |
| `end_time` | Float | 24-hour format, required |
| `duration` | Float | computed: `end_time - start_time`, store=True |

**Constraint `_check_time_validity()`:**
- `start_time` must be in `[0, 24)`.
- `end_time` must be in `[0, 24)`.
- `end_time > start_time`.

**`name_get()`:** Returns display name like `"Monday: 09:00 - 11:00"` — uses `day_of_week.capitalize()` and formats both hours as `HH:MM`.

---

### training.student.line (training_student_line.py)

`_name = 'training.student.line'`
`_rec_name = 'student_id'`

| Field | Type | Notes |
|-------|------|-------|
| `group_id` | Many2one → `training.group` | required, ondelete=cascade |
| `student_id` | Many2one → `res.partner` | required; domain: `[('is_student', '=', True)]` |
| `phone` | Char | related from `student_id.phone`, readonly |
| `mobile` | Char | related from `student_id.mobile`, readonly |
| `lesson_count` | Integer | required, **default=1**; individual lesson count for this student |

**Onchange `_onchange_group_id()`:** When `group_id` is set, auto-fills `lesson_count` from `group_id.lesson_count`.

**SQL constraint:** `UNIQUE(group_id, student_id)` — a student cannot appear in the same group twice.

---

### training.group.delete.wizard (training_group_delete_wizard.py)

`_name = 'training.group.delete.wizard'` (TransientModel)

| Field | Type | Notes |
|-------|------|-------|
| `group_id` | Many2one → `training.group` | readonly |
| `lesson_count` | Integer | readonly; shows how many `lesson.record` entries will be deleted |

**`default_get()`:**
1. Reads `group_id` from `res` (already resolved from context) or falls back to `self.env.context.get('active_id')`.
2. Runs `lesson.record.search_count([('group_id', '=', group_id)])` to populate `lesson_count`.

**`action_confirm_delete()`:**
1. Searches and unlinks all `lesson.record` for `self.group_id`.
2. Calls `self.group_id.with_context(bypass_lesson_check=True).unlink()` — the `bypass_lesson_check=True` context key is passed but the current `training.group.unlink()` does NOT check for it (it always re-deletes lesson.records, which at this point are already gone). This context key is a forward-compatibility signal if a guard is ever added.
3. Returns `{'type': 'ir.actions.act_window_close'}`.

---

## Key Relationships

```
training.group
  ├── schedule_line_ids (One2many → training.schedule.line)  — when/what time lessons happen
  ├── student_line_ids  (One2many → training.student.line)   — who is enrolled + individual lesson count
  └── lesson.record     (via group_id, external model)       — actual lesson instances created by action_start()
        └── lesson.student.line (via lesson_id)              — per-lesson attendance records
```

- `training.group` → `training.schedule.line`: cascade delete (ondelete=cascade on the Many2one side)
- `training.group` → `training.student.line`: cascade delete (ondelete=cascade on the Many2one side)
- `training.group` → `lesson.record`: manually handled in `unlink()` (no DB-level cascade — lesson.record is defined in a separate module)

---

## Sequence (data/sequence.xml)

| Attribute | Value |
|-----------|-------|
| `code` | `training.group` |
| `prefix` | `TRG/` |
| `padding` | 4 |
| `number_increment` | 1 |
| `number_next` | 1 |
| `noupdate` | 1 |

The sequence is declared but **never called** in `create()`. Group names are always entered manually by the user.

---

## Views

### training_group_views.xml

**List view** (`view_training_group_tree`):
Columns: `name`, `teacher_id`, `training_start_date`, `lesson_count`, `student_count`, `state` (badge widget with decoration-info/success/muted), `create_date`.

**Form view** (`view_training_group_form`):
- `save_manually="1"` — requires explicit save; auto-save on navigation is disabled.
- Header buttons:
  - **Start** (`action_start`): `oe_highlight`, visible only when `state != 'pending'` (i.e. shown when state IS pending — Odoo 18 invisible expression).
  - **Modify** (`action_modify`): `btn-secondary`, visible only when `state == 'in_progress'`.
  - **Save** (`special="save"`): always visible.
  - **Discard** (`special="cancel"`): always visible.
  - `state` statusbar widget showing `pending → in_progress → done`.
- Sheet: `name` in `oe_title h1`; two-column group with `teacher_id`, `lesson_count`, `training_start_date`, `start_day_of_week` (left) and `student_count`, `create_date` (right).
- Notebook with two tabs:
  - **Schedule** tab: `schedule_line_ids` editable list with `day_of_week`, `start_time` (float_time), `end_time` (float_time), `duration` (float_time).
  - **Students** tab: `student_line_ids` editable list with `student_id`, `phone`, `mobile`, `lesson_count`.

**Search view** (`view_training_group_search`):
- Search fields: `name`, `teacher_id`, `training_start_date`.
- Filters: Waiting (`state=pending`), Started (`state=in_progress`), Completed (`state=done`).
- Group By: Teacher, Start Date, Status.

**Window action** (`action_training_group`): `list,form` view mode on `training.group`.

**Delete wizard action** (`action_training_group_delete_wizard`):
- Opens `training.group.delete.wizard` form in a dialog (`target="new"`).
- Context: `{'default_group_id': active_id}`.
- Bound to the Action menu on the `training.group` form view via `binding_model_id` + `binding_view_types="form"`.

### training_group_delete_wizard_views.xml

Form with a `alert-warning` div showing the group name and the count of lesson records to be deleted. Footer has **Yes, Delete** (`btn-danger`, calls `action_confirm_delete`) and **Cancel** (`special="cancel"`).

### training_menu.xml

```
Training (root, sequence=10, web_icon references static/description/icon.png)
└── Training Groups (sequence=10, action=action_training_group)
```

---

## Security (ir.model.access.csv)

All four models grant full CRUD (`1,1,1,1`) to `base.group_user` (i.e., all internal users):

| Access ID | Model |
|-----------|-------|
| `access_training_group_user` | `training.group` |
| `access_training_schedule_line_user` | `training.schedule.line` |
| `access_training_student_line_user` | `training.student.line` |
| `access_training_group_delete_wizard_user` | `training.group.delete.wizard` |

No role-based restrictions — any internal user can create, read, write, and delete.

---

## Important Notes

1. **lesson_count duality:** `training.group.lesson_count` (default 20) is the group-wide total used by `action_start()` to generate lesson records. `training.student.line.lesson_count` (default 1) is per-student and used by `action_modify()` to top up individual attendance.

2. **Schedule cycling:** `action_start()` cycles schedule slots: `schedule_index = (lesson_num - 1) % len(schedules)`. With 2 slots and 6 lessons → slots used in order 1, 2, 1, 2, 1, 2.

3. **Onchange sync precision:** `_onchange_lesson_count()` only propagates the new value to student lines whose `lesson_count` still equals the group's previous (`_origin`) lesson_count. Individually customized students are not overwritten.

4. **action_modify() new-lesson scope:** Brand-new `lesson.record` entries created in STEP 2 add ONLY the student with the deficit. Other students are not retroactively added to these extra lessons.

5. **Double unlink (harmless):** The delete wizard unlinks `lesson.record` entries first, then calls `group.unlink()` which searches again and finds an empty set — no error, no data loss.

6. **bypass_lesson_check context key:** Passed by the wizard but not currently checked in `unlink()`. Reserved for future use as a guard flag.

7. **Odoo 18 invisible syntax:** Button `invisible` attributes use Python expressions (e.g., `invisible="state != 'pending'"`), not domain list format.

8. **External model dependency:** `lesson.record` and `lesson.student.line` are referenced throughout but defined in a separate module. This module will fail to install without that module being present.

9. **Sequence unused:** The `TRG/XXXX` sequence in `data/sequence.xml` is installed but never called from Python code. It has no functional effect.

10. **`is_student` domain:** `student_id` on `training.student.line` filters partners by `is_student = True`. This field must be provided by another installed module (e.g., a custom partner extension or the companion module defining `lesson.record`).
