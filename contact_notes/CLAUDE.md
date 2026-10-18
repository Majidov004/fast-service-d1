# contact_notes — Module Map

**Odoo 18 | Technical | Adds tracked, employee-authored notes to res.partner contacts via a custom OWL widget**

Depends: `base`, `contacts`, `hr`, `contact_customization`

---

## File Tree

```
contact_notes/
├── __manifest__.py                        → Module metadata, dependencies, data/asset declarations
├── __init__.py                            → Imports models and wizards packages
│
├── models/
│   ├── __init__.py                        → Imports contact_note, res_partner_note
│   ├── contact_note.py                    → Defines contact.note — the standalone note record model
│   └── res_partner_note.py                → Inherits res.partner — adds note_ids O2M + wizard action
│
├── wizards/
│   ├── __init__.py                        → Imports contact_note_wizard
│   ├── contact_note_wizard.py             → TransientModel for add/edit note dialog
│   └── contact_note_wizard_view.xml       → Form view for the wizard dialog
│
├── views/
│   └── res_partner_notes_view.xml         → Inherits partner form; injects Notes tab with OWL widget
│
├── security/
│   └── ir.model.access.csv                → Read/write/create/unlink grants for all internal users
│
└── static/
    └── src/
        ├── css/
        │   └── contact_notes.css          → Card-based styling for the notes widget
        ├── js/
        │   └── contact_notes_widget.js    → OWL Component: ContactNotesWidget (field widget)
        └── xml/
            └── contact_notes_widget.xml   → QWeb template: contact_notes.NotesWidget
```

---

## Models

### contact.note (`models/contact_note.py`)

| Attribute | Value |
|-----------|-------|
| `_name` | `contact.note` |
| `_description` | `Contact Note` |
| `_order` | `date desc, id desc` |

**Fields**

| Field | Type | Notes |
|-------|------|-------|
| `partner_id` | Many2one → `res.partner` | Required; `ondelete='cascade'` — deleting the partner removes all its notes |
| `employee_id` | Many2one → `hr.employee` | Required; displayed as "Author" |
| `date` | Datetime | Default: `fields.Datetime.now`; `readonly=True` — set at creation, never editable |
| `text` | Text | Required; the note body |

No custom methods — the model is a plain data container. All business logic lives in the wizard and the OWL widget.

---

### res.partner (extension) (`models/res_partner_note.py`)

| Attribute | Value |
|-----------|-------|
| `_inherit` | `res.partner` |

**Additional Fields**

| Field | Type | Notes |
|-------|------|-------|
| `note_ids` | One2many → `contact.note` (via `partner_id`) | String "Notes"; exposes all notes for this partner |

**Methods**

#### `action_open_add_note_wizard(self)`
- Calls `self.ensure_one()` to guard against multi-record calls.
- Returns a dictionary that opens `contact.note.wizard` in a `new` (dialog) window using `ir.actions.act_window`.
- Passes `default_partner_id: self.id` in the context so the wizard pre-populates the partner.
- This method is also callable from Python; the OWL widget does NOT call it — it constructs the action dict directly in JavaScript.

---

## Wizards

### contact.note.wizard (`wizards/contact_note_wizard.py`)

| Attribute | Value |
|-----------|-------|
| `_name` | `contact.note.wizard` |
| `_description` | `Add / Edit Contact Note` |
| Base class | `models.TransientModel` |

**Fields**

| Field | Type | Notes |
|-------|------|-------|
| `partner_id` | Many2one → `res.partner` | Required; hidden in the form view (`invisible="1"`) |
| `note_id` | Many2one → `contact.note` | Optional; if set, the wizard is in edit mode |
| `employee_id` | Many2one → `hr.employee` | Required; string "Author"; default: `self.env.user.employee_id` |
| `text` | Text | Required; string "Note" |

**Methods**

#### `action_save(self)`
1. Calls `self.ensure_one()`.
2. **Edit mode** (`self.note_id` is truthy): calls `self.note_id.write({'text': self.text})` — updates only the text of the existing note. The author and date are not changed on edit.
3. **Create mode** (`self.note_id` is falsy): calls `self.env['contact.note'].create({...})` with `partner_id`, `employee_id`, and `text` from the wizard fields.
4. Returns `{'type': 'ir.actions.act_window_close'}` to close the dialog in both cases.

---

### Wizard View (`wizards/contact_note_wizard_view.xml`)

**Record id:** `view_contact_note_wizard_form`  
**Model:** `contact.note.wizard`  
**View type:** `form`

- `partner_id` — rendered with `invisible="1"` (Python expression, Odoo 18 style); carries the partner context silently.
- `employee_id` — rendered with `readonly="1"`; auto-populated from the current user's employee record; user cannot change it.
- `text` — rendered with `nolabel="1"`, `placeholder="Write your note here…"`, `widget="text"` (multi-line text area).
- Footer buttons:
  - **Save** (`btn-primary`) — calls `action_save` server method.
  - **Cancel** (`btn-secondary`) — `special="cancel"` closes the dialog without saving.

---

## Views (`views/res_partner_notes_view.xml`)

**Record id:** `view_partner_notes_tab`  
**Model:** `res.partner`  
**Inherit from:** `contact_customization.view_partner_form_custom_tabs` (defined in the `contact_customization` dependency)

The view uses an XPath to **replace** the existing `<page name="custom_notes">` entirely:

```xml
<xpath expr="//page[@name='custom_notes']" position="replace">
  <page string="Notes" name="custom_notes">
    <field name="note_ids" widget="contact_notes_widget" nolabel="1"/>
  </page>
</xpath>
```

- The `note_ids` One2many field is rendered using the custom OWL field widget `contact_notes_widget` (registered under that key in the field registry).
- `nolabel="1"` removes the default field label; the widget manages its own header/toolbar.
- No standard list/form sub-view is defined for `note_ids` — the widget handles all rendering.

---

## Static Assets — OWL Widget

### JavaScript (`static/src/js/contact_notes_widget.js`)

**Class:** `ContactNotesWidget` extends `Component`  
**OWL template:** `contact_notes.NotesWidget`  
**Supported field type:** `one2many`  
**Registry key:** `contact_notes_widget` (registered in `registry.category("fields")`)

**Services used:**
- `orm` — for `searchRead` and `unlink` RPC calls.
- `action` — for `doAction` to open wizard dialogs.

**State:** `useState({ notes: [] })` — reactive array of note objects.

**Lifecycle:**
- `onWillStart` → calls `this.loadNotes()` before first render.

**Methods:**

| Method | Description |
|--------|-------------|
| `loadNotes()` | Async. Reads `this.props.record.resId`; if falsy (new unsaved record), returns immediately. Otherwise calls `orm.searchRead('contact.note', [['partner_id','=',id]], ['employee_id','date','text'], {order:'date desc'})` and stores results in `this.state.notes`. |
| `formatDate(dateStr)` | Converts a server Datetime string (space-separated) to a locale-formatted string by appending `T` and `Z` to construct a UTC `Date` object, then calls `toLocaleString` with year/month/day/hour/minute options. |
| `addNote()` | Async. Guards on `resId`. Calls `this.action.doAction(...)` opening `contact.note.wizard` form in a `new` dialog, passing `default_partner_id`. On dialog close (`onClose` callback), calls `this.loadNotes()` to refresh. |
| `editNote(note)` | Async. Same as `addNote` but additionally passes `default_note_id: note.id` and `default_text: note.text` in context, pre-loading the wizard in edit mode. Refreshes on close. |
| `deleteNote(noteId)` | Async. Calls `orm.unlink('contact.note', [noteId])` directly (no confirmation dialog). Then calls `this.loadNotes()` to refresh the list. |

### QWeb Template (`static/src/xml/contact_notes_widget.xml`)

**Template name:** `contact_notes.NotesWidget`

Structure:
- Outer `div.o_contact_notes_wrapper`
  - `div.o_notes_toolbar` — contains an "+ Add Note" button wired to `this.addNote()`.
  - `div.o_contact_notes` (scrollable, max-height 480px) — the note list.
    - If `state.notes.length === 0`: shows `div.o_notes_empty` with text "No notes yet."
    - Otherwise: `t-foreach` over `state.notes`, each rendered as `div.o_note_card`:
      - `div.o_note_header` — flex row with:
        - `div.o_note_meta` — author name (`note.employee_id[1]` or "Unknown") with `fa-user-circle` icon; date string with `fa-clock-o` icon.
        - `div.o_note_actions` — edit button (pencil icon, calls `this.editNote(note)`) and delete button (trash icon with `class="delete"`, calls `this.deleteNote(note.id)`). Actions are invisible until card hover (CSS opacity transition).
      - `div.o_note_body` — note text with `white-space: pre-wrap`.

### CSS (`static/src/css/contact_notes.css`)

Key styling decisions:
- `.o_contact_notes` is capped at `max-height: 480px` with `overflow-y: auto` — long note lists scroll within the tab.
- `.o_note_card` has a distinctive `border-left: 4px solid #875a7b` (Odoo purple accent) to visually separate cards.
- `.o_note_actions` has `opacity: 0` by default; transitions to `opacity: 1` on `.o_note_card:hover` — action buttons appear only on hover.
- `.o_note_actions button.delete:hover` turns red (`color: #e74c3c; background: #fdecea`) to signal destructive action.
- `.o_note_body` uses `white-space: pre-wrap` to preserve newlines entered in the text field.

---

## Security

**File:** `security/ir.model.access.csv`

| id | name | model | group | read | write | create | unlink |
|----|------|-------|-------|------|-------|--------|--------|
| `access_contact_note_user` | access_contact_note_user | `contact.note` | `base.group_user` (all internal users) | 1 | 1 | 1 | 1 |
| `access_contact_note_wizard_user` | access_contact_note_wizard_user | `contact.note.wizard` | `base.group_user` (all internal users) | 1 | 1 | 1 | 1 |

No custom security groups or record rules are defined. All internal users have full CRUD access to both models.

---

## Important Notes

1. **Dependency on `contact_customization`**: The view inherits `contact_customization.view_partner_form_custom_tabs` and replaces the `custom_notes` page using XPath `position="replace"`. If `contact_customization` does not define that page with exactly `name='custom_notes'`, the XPath will fail at module install/upgrade.

2. **OWL widget bypasses standard One2many mechanics**: `note_ids` is declared as a One2many on `res.partner` for data access, but the field is never managed through the standard Odoo list/form inline editor. All CRUD is done via direct ORM RPC calls (`searchRead`, `unlink`) and the wizard dialog inside the OWL component. This means standard Odoo "save/discard" form state does NOT apply to notes — changes take effect immediately (note deletion is instant and irreversible with no confirmation prompt).

3. **No confirmation on delete**: `deleteNote(noteId)` calls `orm.unlink` directly without any browser `confirm()` or Odoo dialog. Clicking the trash icon permanently deletes the note immediately.

4. **Edit mode does not update author or date**: `action_save` in edit mode calls `note_id.write({'text': self.text})` only. The original `employee_id` and `date` on the `contact.note` record remain unchanged. There is no "last edited by" tracking.

5. **Widget does not load notes for unsaved partners**: `loadNotes()` checks `if (!id) return` — on a new partner form that has never been saved, the Notes tab will always show "No notes yet." and the "+ Add Note" button silently does nothing (`if (!id) return` in `addNote()`).

6. **Odoo 18 attribute syntax**: `invisible="1"` and `readonly="1"` in the wizard view XML are scalar Python expressions (truthy constants), which is correct for Odoo 18. Domain-list format (e.g., `[('field','=',value)]`) must not be used for `invisible`/`readonly`/`required` in this version.

7. **`hr` dependency**: The module depends on `hr` because `contact.note.employee_id` links to `hr.employee` and the wizard default is `self.env.user.employee_id`. If an Odoo user has no linked employee record, the wizard's `employee_id` field will be empty and the save will fail validation (field is `required=True`).

8. **`_order` on contact.note**: Records are ordered `date desc, id desc`, so the most recent note always appears first both in ORM queries and in the widget's `loadNotes()` call (which also explicitly passes `order: 'date desc'`).
