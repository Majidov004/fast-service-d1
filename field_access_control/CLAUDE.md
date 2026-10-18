# field_access_control — Module Map

**Odoo 18 | Technical | Per-user field-level access control: hide, readonly, required, mask**

Depends: `base`, `web`

---

## File Tree

```
field_access_control/
├── __manifest__.py
├── __init__.py
├── security/
│   ├── security.xml              → module category + Field Access Manager group
│   └── ir.model.access.csv       → CRUD rights for manager + read-only for base user
├── models/
│   ├── __init__.py
│   ├── field_access_config.py    → per-user config header (field.access.config)
│   ├── field_access_line.py      → individual field rules (field.access.line)
│   └── base_model_patch.py       → _inherit='base' AbstractModel: enforces rules on all models
└── views/
    ├── field_access_views.xml    → form / list / search views + window action
    └── menu_views.xml            → root + child menu (restricted to Field Access Manager)
```

---

## Models

### field.access.config (`field_access_config.py`)

One config record per user. Acts as a header that groups all field rules for that user.

`_rec_name = 'user_id'`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | Many2one → `res.users` | required, ondelete=cascade |
| `active` | Boolean | default=True; if False, NO rules apply for this user |
| `line_ids` | One2many → `field.access.line` | all field rules for this user |
| `note` | Text | free-form note |
| `line_count` | Integer (compute) | `len(line_ids)`, not stored |

**Uniqueness constraint:** `@api.constrains('user_id', 'active')` — only one *active* config is allowed per user. Multiple inactive configs are permitted. SQL-level `UNIQUE` constraint is commented out; a Python-level check is used instead so inactive duplicates can co-exist.

**Methods:**

- **`name_get()`** — Returns `"Sahə Girişi: {user.name}"`.
- **`toggle_active()`** — Defined twice in the file (duplicate). The second definition wins: flips `active` and calls `registry.clear_cache()`. The first definition (no cache clear) is effectively shadowed.
- **`create()` / `write()` / `unlink()`** — All call `self.env.registry.clear_cache()` after the ORM operation to invalidate Odoo's view cache so rule changes take effect immediately.

---

### field.access.line (`field_access_line.py`)

Each record = one rule: one field on one model with one condition and one action.

`_order = 'sequence, id'`

| Field | Type | Notes |
|-------|------|-------|
| `config_id` | Many2one → `field.access.config` | required, ondelete=cascade |
| `sequence` | Integer | default=10; controls evaluation order |
| `active` | Boolean | default=True; inactive lines are skipped |
| `model_id` | Many2one → `ir.model` | target model, ondelete=cascade |
| `model_name` | Char (compute, store=True) | `model_id.model`; used for filtering rules per model |
| `field_id` | Many2one → `ir.model.fields` | target field; domain: `[('model_id','=',model_id)]` |
| `field_name` | Char (related, store=True) | `field_id.name`; used as the key in view XML patching |
| `condition_type` | Selection | `always` / `domain` / `python` |
| `condition_domain` | Char | Odoo domain string, e.g. `[('state','=','draft')]`; used when `condition_type='domain'` |
| `trigger_field_id` | Many2one → `ir.model.fields` | for `field_value` condition (partially implemented, not in UI) |
| `operator` | Selection | `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `like` |
| `trigger_value` | Char | comparison value for `field_value` condition |
| `condition_python` | Text | Python code; available context: `record`, `user`, `env`, `result`; must set `result = True/False` |
| `action` | Selection | `hide` / `readonly` / `required` / `mask` |
| `mask_value` | Char | default=`'***'`; displayed instead of real value when action=mask |
| `note` | Char | |

**Important:** `condition_type` selection only exposes `always`, `domain`, `python` in the UI. `field_value` is handled in `_evaluate()` at the Python level but is NOT selectable from views (the UI fields for it — `trigger_field_id`, `operator`, `trigger_value` — are commented out in the form view).

**`_onchange_model_id()`** — Resets `condition_domain` to `'[]'` and clears `field_id` when the model changes.

**`_evaluate(record)`** — Core method that decides whether this rule applies to a given record:

| condition_type | Logic |
|---|---|
| `always` | Returns `True` unconditionally |
| `domain` | `record.filtered_domain(safe_eval(condition_domain))`; empty domain → `False` |
| `python` | Executes `condition_python` via `safe_eval` with `mode='exec'`; returns `bool(ctx['result'])` |
| `field_value` | Reads `record[trigger_field_id.name]`, applies operator against `safe_eval(trigger_value)`; handles Many2one by using `.id`; supports all 9 operators |

Any exception during evaluation logs a warning and returns `False` (fail-safe).

**ORM overrides:** `create()`, `write()`, `unlink()` all call `registry.clear_cache()`.

---

### BaseFieldAccessPatch (`base_model_patch.py`)

```python
class BaseFieldAccessPatch(models.AbstractModel):
    _inherit = 'base'
```

This is NOT a monkeypatch in the traditional sense — it uses Odoo's standard `_inherit = 'base'` mechanism on an `AbstractModel` to inject methods into every concrete Odoo model. All methods below apply to every model in the system.

**Superuser exemption:** All methods call `_get_field_access_rules()` first. If the user is a superuser (`user._is_superuser()`), an empty recordset is returned and no rules are enforced.

---

#### Module-level helper: `_domain_to_py_expr(domain_str)`

Converts an Odoo domain string to a Python boolean expression compatible with Odoo 18's `invisible`/`readonly`/`required` XML attributes.

**Why needed:** In Odoo 18, view attributes like `invisible` must be Python expressions (`state == 'draft'`), not domain lists. A non-empty list like `[('state','=','draft')]` would always evaluate to `True` as a Python expression.

**Conversion map:**

| Domain operator | Python expression |
|---|---|
| `=` | `==` |
| `!=` | `!=` |
| `>`, `<`, `>=`, `<=` | same |
| `in`, `not in` | same (value as repr) |

**Limitations:** Boolean operators `&`, `|`, `!` are silently skipped. Only simple flat domains with AND logic are fully supported. Complex nested domains will produce incorrect or partial results.

---

#### Methods injected into all models:

**`_get_field_access_rules()`**

- Returns empty recordset for superusers.
- Searches `field.access.config` (with `sudo()`) for an active config matching `env.user`.
- Filters `config.line_ids` to only those that are active and have `model_name == self._name`.

**`_get_view_cache_key(view_id, view_type, **options)`**

- Extends the default cache key tuple with: `(uid, config.id, config.active, config.write_date, last_line_write_date)`.
- Critical for correctness: without this override, Odoo would serve the same cached XML view to all users, ignoring per-user field visibility rules.
- `last_line_date` is `max(line_ids.mapped('write_date'))` — ensures any line change busts the cache.

**`fields_get(allfields, attributes)`**

- Only processes `condition_type='always'` rules (not `domain` or `python` — those depend on record data not available at schema level).
- `hide` → sets `invisible=True`, `searchable=False`, `exportable=False` on the field metadata dict.
- `readonly` → sets `readonly=True`.
- `required` → sets `required=True`.
- Does NOT set `mask` here (mask is handled in `read()`).

**`read(fields, load)`**

- Calls `super().read()` first, then post-processes the result list.
- For each record dict, browses the actual record and evaluates all rules via `_evaluate()`.
- `hide` action → replaces `rec_dict[fname]` with `False`.
- `mask` action → replaces `rec_dict[fname]` with `rule.mask_value` (default `'***'`).
- `readonly` and `required` actions are not enforced here (they apply in `write()`/`create()`).

**`write(vals)`**

- Iterates each record and each rule; calls `_evaluate(record)`.
- `readonly` → raises `ValidationError` if the protected field name is present in `vals`.
- `required` → raises `ValidationError` if the field would be empty after write (checks `vals.get(fname)` falling back to current `record[fname]`).

**`create(vals_list)`**

- Calls `super().create()` first, then checks `required` rules on the newly created records.
- Raises `ValidationError` if a required field is empty on the new record.
- Note: `hide`/`readonly`/`mask` are not checked at create time.

**`_get_view(view_id, view_type, **options)`**

Patches the view XML (lxml arch) in-place before returning it to the client.

*`always` rules:*
- Locates `//field[@name='{fname}']` nodes via XPath.
- `hide` → sets `invisible="1"` and `column_invisible="1"` on field nodes; sets `invisible="1"` on matching `//label[@for='{fname}']`; sets `nolabel="1"` on the field node.
- `readonly` → sets `readonly="1"`.
- `required` → sets `required="1"`.

*`domain` rules:*
- Converts `condition_domain` to a Python expression via `_domain_to_py_expr()`.
- If conversion yields a non-empty string, injects it as the attribute value (e.g. `invisible="state == 'draft'"`).
- Same `hide`/`readonly`/`required` attribute mapping as above, using the expression string instead of `"1"`.
- `mask` action is not handled in `_get_view()` (masking is a data-level concern, handled in `read()`).

*`python` rules:*
- NOT handled in `_get_view()` — Python condition rules only apply at the data level (`read()`, `write()`, `create()`), not as XML attributes.

---

## Security

### Group: `Field Access Manager`

Defined in `security/security.xml`:
- Module category: `Field Access Control`
- `implied_ids`: includes `base.group_user` (internal user)

### Access Rights (`ir.model.access.csv`)

| Access ID | Model | Group | R | W | C | D |
|-----------|-------|-------|---|---|---|---|
| `access_field_access_config_manager` | `field.access.config` | Field Access Manager | 1 | 1 | 1 | 1 |
| `access_field_access_line_manager` | `field.access.line` | Field Access Manager | 1 | 1 | 1 | 1 |
| `access_field_access_config_user` | `field.access.config` | `base.group_user` | 1 | 0 | 0 | 0 |
| `access_field_access_line_user` | `field.access.line` | `base.group_user` | 1 | 0 | 0 | 0 |

Regular internal users get read-only access to configs/lines so `_get_field_access_rules()` (which uses `sudo()`) can read their own rules at runtime. Only managers can create/edit/delete rules.

---

## Views

### `field_access_views.xml`

- **`view_field_access_config_form`** — Form view for `field.access.config`:
  - Header: `toggle_active` button.
  - `web_ribbon` widget shows "Arxivlənib" (archived) when `active=False`.
  - `line_ids` embedded with both list (sequence handle, model, field, condition_type, action, active toggle) and inline form.
  - Inline form: `mask_value` shown/required only when `action='mask'`; `condition_domain` with `widget="domain"` shown only when `condition_type='domain'`; `condition_python` shown only when `condition_type='python'`.
  - `trigger_field_id`, `operator`, `trigger_value` fields are commented out in the form (field_value condition not exposed in UI).

- **`view_field_access_config_list`** — List view: user, rule count, active toggle.

- **`view_field_access_config_search`** — Search view: by user; filters for Active / Archived.

- **`action_field_access_config`** — Window action: `list,form`; default filter: `search_default_active=1`.

### `menu_views.xml`

- Root menu: `Sahə Giriş Nəzarəti` — restricted to `group_field_access_manager`; references `static/description/icon.png` (file not present in repo, referenced only in manifest-level menu icon).
- Child menu: `Konfiqurasiyalar` → opens `action_field_access_config`.

---

## End-to-End Flow

```
Admin (Field Access Manager):
  Creates field.access.config for user X
    └── Adds field.access.line:
          model=res.partner, field=phone, condition=always, action=hide

User X opens any res.partner record:
  1. _get_view()     → phone XML node gets invisible="1", column_invisible="1", nolabel="1"
  2. fields_get()    → phone metadata: invisible=True, searchable=False, exportable=False
  3. read()          → phone value in response dict replaced with False
  4. write({phone:…})→ ValidationError if action were readonly (for hide, no write protection)
```

---

## Important Notes

- **Scope:** `_inherit = 'base'` means every Odoo model is affected, including system models. Superusers (`_is_superuser()`) are always exempt.
- **Cache invalidation:** `registry.clear_cache()` is called in `create/write/unlink` of both `field.access.config` and `field.access.line`. This is mandatory — Odoo caches `_get_view()` output aggressively. Without cache clearing, rule changes would not be visible until a server restart.
- **Per-user view cache:** `_get_view_cache_key()` ensures each user gets an independently cached view keyed on their config state. Without this, the first user to load a view would cache it for everyone.
- **`field_value` condition type:** Fully implemented in `_evaluate()` (supports all 9 operators, handles Many2one `.id` extraction) but NOT exposed in the UI — the `condition_type` Selection field only lists `always`, `domain`, `python`. The related UI fields are commented out in the form view.
- **`toggle_active()` duplicate:** The method is defined twice in `field_access_config.py`. Python's class definition means the second definition (which includes `registry.clear_cache()`) overwrites the first. This is a code defect — the first definition is dead code.
- **Mask is UI-only:** `mask` action replaces read values with `mask_value` in the API response, but the real data remains in the database. Users with direct DB access or API access (bypassing this module) can still read the real value.
- **Domain-to-Python conversion for `_get_view()`:** Only flat domains with equality/comparison operators convert correctly. `&`/`|`/`!` (complex boolean logic) are silently dropped. A domain like `['|', ('state','=','draft'), ('state','=','sent')]` would produce `"state == 'draft'"` (incorrect — second clause is lost).
- **`python` condition and `_get_view()`:** Python-condition rules are NOT injected into the XML view. They only apply at data level (read/write/create). There is no client-side enforcement for python-condition rules — only server-side.
- **No `data/` or `wizards/` or `static/` directories** in the actual module (the `static/description/icon.png` referenced in `menu_views.xml` is not present as a file in the repo).
