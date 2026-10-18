# hr_employee_onboarding — Module Map

**Odoo 18 | HR extension | Send login credentials to new employees and redirect them to their profile on first login**

Depends: `base`, `hr`, `mail`

---

## File Tree

```
hr_employee_onboarding/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv    → header-only (no custom model ACL rows needed)
├── data/
│   └── mail_template.xml      → defines a mail.template record (reference/visual copy);
│                                  actual email is sent inline via mail.mail in Python
├── models/
│   ├── __init__.py
│   ├── res_users.py           → onboarding_done field + invite action
│   └── hr_employee.py         → onboarding_done computed proxy + complete action
└── views/
    ├── res_users_views.xml    → two-state buttons + badge on user form header
    └── hr_employee_views.xml  → warning banner + "Complete" button on employee form header
```

---

## Models

### res.users (res_users.py) — ResUsers (`_inherit = 'res.users'`)

**New field**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `onboarding_done` | `Boolean` | `False` | Set to True after employee completes their profile |

---

**`_generate_password(length=10)`**

Generates a random 10-character alphanumeric password using `secrets.choice` over `string.ascii_letters + string.digits`. Returns a plain-text string that Odoo hashes automatically when written to the `password` field.

---

**`action_send_onboarding_invite()`**

Called from the "Send Onboarding Invite" / "Re-send Onboarding Invite" button on the user form.

Steps:
1. `ensure_one()` — must be called on a single user record.
2. Validates `self.email` — raises `UserError` if missing.
3. Searches `hr.employee` for a record where `user_id == self.id` (limit 1) — raises `UserError` if not found.
4. Generates a random password via `_generate_password()` and writes it with `self.sudo().write({'password': password})`.
5. Creates a new `ir.actions.act_window` record (via `sudo()`) with:
   - `name`: `'Complete My Profile'` (used later for identification/cleanup)
   - `res_model`: `'hr.employee'`
   - `res_id`: the linked employee's ID
   - `view_mode`: `'form'`
   - `target`: `'current'`
6. Writes `action_id = <new action>` and `onboarding_done = False` on the user (via `sudo()`). Setting `user.action_id` causes Odoo to redirect the user to the employee form immediately after login.
7. Resolves `base_url` from `ir.config_parameter` (`web.base.url`) to build `login_url = base_url + '/web/login'`.
8. Determines `from_email`: prefers `self.env.user.email`, falls back to `mail.default.from` system parameter, then `'noreply@example.com'`.
9. Builds a styled HTML email body inline (Python string concatenation) in Azerbaijani. Layout:
   - Purple (`#875A7B`) header: "Welcome to Odoo 🎉"
   - Table with: login URL (linked), username (`self.login`), password (highlighted in purple, letter-spacing)
   - Yellow warning box: fill profile then click **Complete**
   - CTA button: "Odoo-ya Daxil Ol"
   - Gray footer: auto-send disclaimer
10. Creates a `mail.mail` record (via `sudo()`) with `subject`, `body_html`, `email_to`, `email_from` and immediately calls `.send()`.
11. Returns a green `display_notification` client action: title "Invite Sent", message "Login credentials have been sent to {email}".

**Note:** The `mail_template.xml` defines a `mail.template` with the same visual design and Jinja2 variables (`{{ ctx.get('password') }}`, `{{ ctx.get('login_url') }}`). However, `action_send_onboarding_invite()` does NOT use this template — it sends the email via `mail.mail` with inline HTML. The template is a reference copy that could be used for manual sending from the Templates menu.

---

### hr.employee (hr_employee.py) — HrEmployee (`_inherit = 'hr.employee'`)

**New field**

| Field | Type | store | Notes |
|-------|------|-------|-------|
| `onboarding_done` | `Boolean` (compute + inverse) | `False` | Non-stored proxy; reads/writes `user_id.onboarding_done` |

---

**`_compute_onboarding_done()`**

For each record: `rec.onboarding_done = rec.user_id.onboarding_done if rec.user_id else True`.
If no linked user, treated as "already done" (True) so buttons/banners remain hidden.

---

**`_inverse_onboarding_done()`**

For each record: if `rec.user_id` exists, writes the value back via attribute assignment:
`rec.user_id.sudo().onboarding_done = rec.onboarding_done`.
(Uses attribute assignment rather than `.write()` — equivalent effect, Odoo triggers field write.)

---

**`action_complete_onboarding()`**

Called from the "Complete" button on the employee form. Marks onboarding as finished.

Steps:
1. `ensure_one()`.
2. Retrieves `user = self.user_id`.
3. If `user` exists:
   - Saves reference to `old_action = user.sudo().action_id`.
   - Writes `action_id = False` and `onboarding_done = True` on the user in a single `sudo().write({...})`.
   - If `old_action` exists and `old_action.name == 'Complete My Profile'`, calls `old_action.sudo().unlink()` to clean up the temporary action record.
4. Posts a chatter note via `self.message_post(body=..., subtype_xmlid='mail.mt_note')`:
   `"<b>✅ Onboarding completed.</b> Employee profile has been filled in."`
5. Returns `{'type': 'ir.actions.client', 'tag': 'home'}` — navigates the user to the normal Odoo home screen.

---

## data/mail_template.xml

Defines a `mail.template` record (with `noupdate="1"`):

| Attribute | Value |
|-----------|-------|
| External ID | `mail_template_onboarding_invite` |
| Name | `HR Onboarding – Login Invite` |
| Model | `res.users` |
| Subject | `Welcome to Odoo – Your Login Details` |
| `email_to` | `{{ object.email }}` |

Body uses Jinja2 context variables:
- `{{ ctx.get('employee_name', object.name) }}` — employee display name
- `{{ ctx.get('login_url') }}` — Odoo login URL
- `{{ object.login }}` — username
- `{{ ctx.get('password') }}` — the generated password

**Important:** This template is NOT called by any Python code in the module. It is a visual reference copy with the same design as the inline email. To use it programmatically, one would call `template.with_context(password=..., login_url=...).send_mail(user.id)`.

---

## Views

### res_users_views.xml

Inherits `base.view_users_form`. Injects into the `<header>` area:

| Element | Condition | Notes |
|---------|-----------|-------|
| Button "Send Onboarding Invite" (`btn-primary`, envelope icon) | `invisible="onboarding_done == True"` | Shown when invite not yet sent / user not done; has confirmation dialog in Azerbaijani |
| Button "Re-send Onboarding Invite" (`btn-secondary`, envelope icon) | `invisible="onboarding_done == False"` | Shown only after onboarding is done (allows re-sending) |
| `<span>` badge "✅ Onboarding Done" (`badge text-bg-success`) | `invisible="not onboarding_done"` | Green badge visible when `onboarding_done = True` |
| `<field name="onboarding_done" invisible="1"/>` | always | Hidden field injected after `login` field so the view can reference it |

Both buttons call the same method `action_send_onboarding_invite` (type `object`).

### hr_employee_views.xml

Inherits `hr.view_employee_form`. Inserts a new `<header>` block before `<sheet>`:

| Element | Condition | Notes |
|---------|-----------|-------|
| Warning `<div>` (Bootstrap `alert-warning`, full-width) | `invisible="onboarding_done"` | Shown when onboarding is NOT done; instructs employee to fill profile and click Complete; text in Azerbaijani |
| Button "Complete" (`btn-success`, check-circle icon) | `invisible="onboarding_done"` | Calls `action_complete_onboarding`; has confirmation dialog in Azerbaijani |
| `<field name="onboarding_done" invisible="1"/>` | always | Hidden field for reactivity |

---

## Security

`security/ir.model.access.csv` — contains the CSV header only with no data rows:
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```
No custom model access rules are defined. The module relies on existing ACL from `base` and `hr`. All sensitive writes (password, action_id, unlink) use `sudo()` to bypass record rules.

---

## Onboarding Flow

```
ADMIN SIDE
──────────
Admin: Settings → Users → opens user form
  └─ Sees "Send Onboarding Invite" button (if onboarding_done == False)
  └─ Clicks button → confirmation dialog
        └─ action_send_onboarding_invite() runs:
              1. Validates email + linked hr.employee
              2. Generates random 10-char password, writes to user
              3. Creates ir.actions.act_window "Complete My Profile" → employee form
              4. Sets user.action_id = new action, onboarding_done = False
              5. Builds inline HTML email in Azerbaijani
              6. Sends via mail.mail (not template)
              7. Returns success notification toast

EMPLOYEE SIDE
─────────────
Employee: Receives email with link, username, password
  └─ Opens /web/login, enters credentials
  └─ Odoo detects user.action_id is set → redirects to employee form instead of home
  └─ Yellow warning banner visible: "fill your profile and click Complete"
  └─ Employee fills in profile fields
  └─ Clicks "Complete" button → confirmation dialog
        └─ action_complete_onboarding() runs:
              1. Sets user.action_id = False (removes forced redirect)
              2. Sets user.onboarding_done = True
              3. Deletes the temporary ir.actions.act_window record
              4. Posts chatter note "✅ Onboarding completed."
              5. Redirects to {'tag': 'home'} — normal Odoo dashboard

AFTER COMPLETION
────────────────
Admin: User form shows "Re-send Onboarding Invite" + green "✅ Onboarding Done" badge
Employee: Next login goes to normal Odoo home (no redirect)
```

---

## Important Notes

- **Password handling:** Password is set in plain text via `sudo().write({'password': ...})` — Odoo's ORM automatically hashes it (bcrypt). The generated password is only visible in the email.
- **Temporary redirect:** Each invite call creates a new `ir.actions.act_window` record. The old one is deleted at completion time (identified by name `'Complete My Profile'`). If `action_send_onboarding_invite()` is called multiple times without completing, orphaned action records can accumulate.
- **Re-send behavior:** The "Re-send" button (visible when `onboarding_done == True`) calls the same method — it resets `onboarding_done = False` and creates another redirect action, effectively restarting the onboarding cycle.
- **Non-stored proxy field:** `onboarding_done` on `hr.employee` is a compute+inverse field with `store=False`. The authoritative value lives on `res.users.onboarding_done`.
- **No linked user:** If `hr.employee.user_id` is False, `_compute_onboarding_done` returns `True`, hiding all onboarding UI elements on the employee form.
- **Email sender:** Resolved dynamically — uses the admin's email if available, otherwise `mail.default.from` system parameter, otherwise `noreply@example.com`.
- **mail_template.xml vs inline email:** The module ships both a `mail.template` record (for reference/manual use) and inline HTML email logic in Python. The template is NOT called programmatically — it exists as a design reference and can be triggered manually from the Odoo Email Templates menu.
- **Odoo 18 invisible syntax:** View attributes use Python expression format (`invisible="onboarding_done == True"`, `invisible="not onboarding_done"`), NOT domain list format — compliant with Odoo 18.
- **No custom ACL rows:** The CSV security file is empty (header only). All privilege escalation uses `sudo()`.
