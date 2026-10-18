# access_manager — Module Map

**Odoo 18 | Technical | Per-user AND per-role (position) CRUD permissions, record-level filter rules and status filters via global ir.rule**

Depends: `base`, `mail`

> **İki rejim:**
> - **Per-user** (`access.config`) — bir istifadəçiyə fərdi icazə (orijinal funksiya).
> - **Per-role/vəzifə** (`access.role`) — bir vəzifəyə (məs. "Müəllim") icazə bir dəfə təyin olunur, sonra istifadəçilərə həmin vəzifə verilir (res.users.`access_role_ids`). Hamısı eyni icazəni alır; fərdi istisna `access.config` ilə üstdən verilir.

---

## File Tree

```
access_manager/
├── __manifest__.py
├── __init__.py
├── security/
│   └── ir.model.access.csv
├── models/
│   ├── __init__.py
│   ├── access_config.py            → per-user config header
│   ├── access_config_line.py       → per-model CRUD + filter rules (per-user)
│   ├── access_status_value.py      → status filter values (child of config line)
│   ├── access_role.py              → per-role/vəzifə config header (+ real group sync)
│   ├── access_role_line.py         → per-model CRUD + filter rules (per-role)
│   ├── access_role_status_value.py → status filter values (child of role line)
│   └── res_users.py                → access_role_ids (vəzifə təyini) + sync hooks
├── static/description/
│   └── index.html
└── views/
    ├── access_config_views.xml  → per-user form/list/search views
    ├── access_role_views.xml    → per-role views + res.users form page
    └── menu_views.xml           → Administration menu entries (Vəzifələr + İstifadəçi İcazələri)
```

---

## Models

### access.config (access_config.py)

One config per user. Contains all model-level permission lines.

`_inherit = ['mail.thread', 'mail.activity.mixin']` | `_rec_name = 'user_id'`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | Many2one → res.users | required, ondelete=cascade, index=True, tracking=True |
| `line_ids` | One2many → access.config.line | all permission lines |
| `line_count` | Integer | compute |
| `state` | Selection | draft/applied; tracking=True, readonly=True |
| `last_apply_date` | Datetime | readonly; set when applied |
| `note` | Text | |

**SQL constraint:** UNIQUE(user_id) — one config per user

**`action_apply()`**:
1. Validates user is not admin (uid=1 is blocked)
2. Calls `line._apply()` for each line → creates/updates ir.model.access + ir.rule
3. Sets `state='applied'`, updates `last_apply_date`
4. Clears registry cache
5. Returns success notification

**`action_reset()`**:
1. Calls `line._cleanup()` for each line → deletes ir.model.access + ir.rule
2. Sets `state='draft'`, clears `last_apply_date`
3. Clears registry cache
4. Returns warning notification

**`unlink()`**: calls `_cleanup()` for all lines before deleting the config, then clears cache

---

### access.config.line (access_config_line.py)

One line = one model's CRUD permissions + optional record filter + optional status filter for the user.

| Field | Type | Notes |
|-------|------|-------|
| `config_id` | Many2one → access.config | ondelete=cascade, index=True |
| `user_id` | Many2one (related from config_id) | store=True, index=True |
| `model_id` | Many2one → ir.model | required; domain: transient=False |
| `model_name` | Char | related from model_id.model, store=True |
| `perm_read` | Boolean | default=True |
| `perm_write` | Boolean | default=False |
| `perm_create` | Boolean | default=False |
| `perm_unlink` | Boolean | default=False |
| `filter_mode` | Selection | all/own/own_plus; default='all' |
| `user_field_id` | Many2one → ir.model.fields | Many2one/Many2many field on the model pointing to the responsible user |
| `visible_user_ids` | Many2many → res.users | extra users whose records are also visible (own_plus mode only) |
| `active` | Boolean | default=True |
| `status_field_id` | Many2one → ir.model.fields | selection-type field on the model; if set, only records with allowed statuses are visible |
| `status_value_ids` | One2many → access.status.value | allowed status key values |
| `available_values_hint` | Char | compute: shows available selection values for status_field_id (info only) |
| `access_id` | Many2one → ir.model.access | readonly; reference to created ACL |
| `rule_id` | Many2one → ir.rule | readonly; reference to created record rule |

**filter_mode values:**
- `all` → no ownership filtering (status filter can still apply)
- `own` → user sees only records where user_field points to them
- `own_plus` → own records + selected visible_user_ids' records

**SQL constraint:** UNIQUE(config_id, model_id)

**Onchanges:**
- `_onchange_model_id()`: resets user_field_id, visible_users, status_field_id, status_value_ids; auto-selects `user_id` field if model has one
- `_onchange_status_field_id()`: clears status_value_ids when status field changes
- `_onchange_filter_mode()`: clears visible_user_ids when mode != 'own_plus'

**Constraints:**
- user_field must belong to the selected model
- visible_users only allowed for own_plus mode
- user cannot add themselves to visible_users

---

### access.status.value (access_status_value.py)

Child model — each record is one allowed status key value for a config line.

| Field | Type | Notes |
|-------|------|-------|
| `line_id` | Many2one → access.config.line | required, ondelete=cascade, index=True |
| `value` | Char | required; the selection key (e.g. 'draft', 'planned', 'done') |

Used by `_build_domain()` to construct the status part of the ir.rule domain.

---

### Core Technical Methods

**`_get_user_field_path()`**:
Determines the domain field path based on the related model of `user_field_id`:
- `user_field_id` empty → `'create_uid'`
- Relation = `res.users` → `field_name`
- Relation = `res.partner` → `field_name.user_ids`
- Relation = `hr.employee` → `field_name.user_id`
- Other → `field_name.user_id` (assumed)

**`_build_domain()`**:
Builds a Python expression for `ir.rule.domain_force`. Combines TWO independent filters with AND:

1. **User ownership filter** (when filter_mode != 'all'):
   ```python
   ('field_path', 'in', [uid1, uid2, ...])
   ```
2. **Status filter** (when status_field_id + status_value_ids are set):
   ```python
   ('status_field_name', 'in', ['draft', 'done', ...])
   ```

Full domain wrapped in ternary:
```python
[(<ownership_cond>, <status_cond>)] if user.id == TARGET_UID else [(1, '=', 1)]
```
- If only one filter exists, only that condition is used
- If neither exists, returns `[(1, '=', 1)]` (no restriction)
- Ternary ensures the rule only restricts the TARGET user; all others see everything

**`_apply()`**:
1. Gets/creates a hidden group for the user via `_get_or_create_user_group()`
2. Creates/updates `ir.model.access` (ACL) linked to that group with the CRUD permissions
3. Checks `needs_rule = (filter_mode != 'all' OR has_status_filter) AND active`
   - If needs_rule: creates/updates global `ir.rule` (groups=empty → applies to ALL users, but domain_force ternary limits to target user)
   - If not needs_rule: deletes any existing rule
4. Saves `access_id` and `rule_id` references on the line

**`_cleanup()`**: Deletes the linked `ir.rule` and `ir.model.access` records, clears references

**`_get_or_create_user_group()`**:
- Searches for existing group via SQL (jsonb-aware for Odoo 18's `name` field):
  ```sql
  SELECT rg.id FROM res_groups rg
  JOIN res_groups_users_rel rgu ON rgu.gid = rg.id
  WHERE rgu.uid = %s AND rg.name->>'en_US' LIKE '[AccessMgr]%'
  ```
- Creates if not found: `[AccessMgr] {user.name} (id:{uid})`
- The group contains only this user and is used solely for ACL binding

**`unlink()`**: calls `_cleanup()` + clears registry cache

---

## Role-Based Access (access.role) — Per-Vəzifə

İstifadəçiləri tək-tək konfiqurasiya etmək əvəzinə bir **vəzifə** (rol) üçün
icazələri bir dəfə təyin edib, istifadəçiləri o vəzifəyə əlavə etmək imkanı.

### access.role (`access_role.py`)

One config per **position/role** (NOT per user). `_inherit = ['mail.thread','mail.activity.mixin']`, `_rec_name='name'`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | required, tracking; UNIQUE(name) |
| `group_id` | Many2one → res.groups | readonly, technical — the **real** backing group `[AccessRole] {name}` |
| `member_user_ids` | Many2many → res.users | members; **shares relation `access_role_users_rel`** with `res.users.access_role_ids` (editable from both sides) |
| `line_ids` | One2many → access.role.line | permission lines |
| `member_count` / `line_count` | Integer | compute |
| `state` | Selection | draft/applied; tracking, readonly |
| `last_apply_date` | Datetime | readonly |
| `note` | Text | |

**Key methods:**
- `_ensure_group()` — creates/returns the real group `[AccessRole] {name}`; stores `group_id`. (No SQL lookup — group_id stored directly; prefix `[AccessRole]` deliberately does **NOT** match the per-user `[AccessMgr]%` SQL LIKE → no collision.)
- `_sync_group_members()` — sets `group_id.users = member_user_ids` (admin uid=1 always filtered out, never raises).
- `action_apply()` — ensure group → sync members → `line._apply()` per line → state=applied → `registry.clear_cache()`.
- `action_reset()` — `line._cleanup()` per line + empties group's users + state=draft.
- `write()` — on `name` change updates group name; on `member_user_ids` change re-syncs group + clears cache (so adding the 11th member takes effect **immediately, no re-apply**).
- `unlink()` — cleanup lines + delete the backing group.
- **`is_dependency` (Boolean) on access.role.line** splits lines into two One2many views on access.role: `line_ids` (domain `is_dependency=False`, manually-added primary models, **tab 2 "İcazə Sətirləri"**) and `dependency_line_ids` (domain `is_dependency=True`, auto-discovered, **tab 3 "Alt Asılılıqlar"**). `_all_lines()` = union of both; `action_apply`/`action_reset`/`unlink`/`_compute_counts` all operate on `_all_lines()` so BOTH tabs are applied/cleaned.
- `action_discover_dependencies()` / `_discover_model_deps(model_name)` — **header button "Asılılıqları Tap"**. For each model in `_all_lines()`, auto-adds **dependency lines (is_dependency=True → tab 3)**: related (form/list-referenced, non-transient) models → **read-only**; wizard (transient) models → **read+write+create**. Discovery combines 4 sources: `get_views(['form','list'])['models']`, form `<button type="action">` → act_window res_model, act_window bound by `binding_model_id`/`res_model`, and a **naming heuristic** (`<model>.%` transient models, e.g. `trail.lesson.complete.wizard`). NOT exhaustive — `type="object"` method-launched wizards and Python-`create()`d models (e.g. `finance.cash.move`) can't be found statically. Skips models already present (in either tab); re-running expands the next level. Added lines stay draft until `action_apply()`.

> **Note:** `model_id` domain on both `access.config.line` and `access.role.line` no longer filters `transient=False` — **wizard (TransientModel) models are now selectable** (needed to grant wizard ACLs, e.g. `trail.lesson.complete.wizard`). For transient models leave `filter_mode='all'` (no ir.rule is built when filter_mode='all' and no status filter).

### access.role.line (`access_role_line.py`)

Mirror of `access.config.line` but applies to ALL role members. Differences:
- `role_id` (instead of `config_id`); **no** `user_id`. UNIQUE(role_id, model_id).
- ACL name `access_role_acl_r{role}_m{model}`, bound to `role_id.group_id`.
- Rule name `access_role_rule_r{role}_m{model}`, **global** (`groups=[(5,0,0)]`).
- **`_build_domain()` — the critical difference:**
  ```python
  "<inner_filter> if <group_id> in user.groups_id.ids else [(1, '=', 1)]"
  ```
  - Gate is **group membership** (`user.groups_id.ids`), not a single uid → applies to all members, no-op for everyone else.
  - For `own`/`own_plus`, the ownership condition uses **dynamic `user.id`** (literal text `user.id` inside the domain string, evaluated per current user) — `[('field_path','in',[user.id, ...extras])]`. **Must stay dynamic**: a static union of member ids would let every member see every other member's records (security bug).
- `_get_user_field_path()`, onchange, `_compute_available_values_hint`, constraints — duplicated from `access.config.line` (same logic).

### access.role.status.value (`access_role_status_value.py`)
Child of `access.role.line` (line_id + value Char) — same shape as `access.status.value`.

### res.users (`res_users.py`)
- `access_role_ids` Many2many → access.role (relation `access_role_users_rel`, columns swapped vs the role side → same table, bidirectional).
- `write()`/`create()` — when `access_role_ids` changes, `_resync_access_roles()` re-syncs **all applied** roles' group membership + clears cache. (Writing `group.users` does NOT recurse into res.users.write.)

### Why this combines correctly (Odoo semantics)
- **Role grant** = ACL on the role group → **UNION** across the user's groups (adds CRUD to all members).
- **Role restrict** = **global** ir.rule gated by group membership → **AND** (only the way to restrict members below their broad Internal-User access; a *group* rule would OR-widen and fail to restrict).
- **Per-user exception** = existing `access.config` on top: extra grant (ACL union) ✅, extra record filter (global rule AND) ✅. **Revoking a CRUD verb the role granted is impossible** (ACL has no deny) → remove the user from the role instead.
- Linchpin verified in Odoo source (`base/models/ir_rule.py:_eval_context`): the rule eval context exposes `user = env.user`, so `user.groups_id` / `user.id` are valid inside `domain_force`. Group-membership changes auto-clear the registry cache → **no stale-domain problem**.

---

## Technical Architecture

```
access.config (one per user)
  └─ access.config.line (one per model)
        ├─ access.status.value (child — allowed status values)
        ├─ ir.model.access → grants CRUD to [AccessMgr] group
        │     └─ user is in [AccessMgr] group → gets these permissions
        └─ ir.rule (global, groups=empty) → record filter
              domain_force: "[cond1, cond2] if user.id == TARGET else [(1,'=',1)]"
              cond1: ownership (field_path in allowed_uids)
              cond2: status (status_field in allowed_values)
              └─ Only TARGET user gets filtered; others unaffected
```

**Why global rules (groups=empty)?**
Internal User group's ACL already grants broad access. User-specific ACL alone can't override that. Global rules (no groups) apply on top of all group permissions — they're the only way to restrict a user who inherits broad access from their group.

---

## Views (access_config_views.xml)

**Line form (popup):**
- Model + CRUD toggles (perm_read/write/create/unlink as boolean_toggle)
- Record Filter section: filter_mode (radio) + user_field_id (hidden when filter_mode=all) + visible_user_ids (hidden when not own_plus)
- Status Filter section: status_field_id (selection type only) + available_values_hint (readonly info) + status_value_ids (editable list of key values)
- Technical section: access_id + rule_id (readonly)

**Config form:**
- Header: "İcazələri Tətbiq Et" (btn-primary) + "Sıfırla" (btn-secondary, hidden when draft, has confirm dialog)
- Title: user_id (many2one_avatar_user, readonly after save)
- Stats: last_apply_date + line_count
- Lines tab: list with columns: model_id, filter_mode, visible_user_ids (tags), user_field_id (optional), CRUD toggles, active

**Config list:**
- Columns: user_id (avatar), line_count, last_apply_date, state (badge)
- decoration-success when applied, decoration-muted when draft
- Inline "Tətbiq et" button per row

**Search:** filter by user_id; filters: Applied/Draft; group by: state

---

## Security & Access

**ir.model.access.csv** grants full CRUD exclusively to `base.group_system` (Settings / Administrator group) for all three module models (`access.config`, `access.config.line`, `access.status.value`). Regular users have no direct access to these configuration records.

**Menu** (`menu_views.xml`) — root menu "İcazə İdarəetməsi" and its child "İstifadəçi İcazələri" are both restricted to `base.group_system`. The root menu also sets a custom `web_icon` from `static/description/icon.png`.

---

## Important Notes

- Admin (uid=1) is protected — `action_apply()` raises UserError for admin
- `action_apply()` must be called explicitly — creating lines alone does nothing
- `action_reset()` removes ALL generated ACLs and rules — the user loses all configured permissions
- Global rules with ternary domain: the rule applies to ALL users but the ternary means only the target user is affected; this is intentional and safe
- The generated `ir.rule` always has all four `perm_read/write/create/unlink = True` (the rule is a record filter, not a permission grant — CRUD scope is controlled by the ACL, not the rule)
- The [AccessMgr] hidden group is created once per user and reused across all their ACL lines
- `registry.clear_cache()` after every change ensures Odoo picks up new ACL/rule state immediately
- `ir.rule` with `groups=[(5,0,0)]` = truly global (no groups bound)
- Odoo 18 stores `res_groups.name` as JSONB — the `_get_or_create_user_group()` SQL uses `->>'en_US'` to search by English name
- Status filter works together with ownership filter using AND logic — both must be satisfied for a record to be visible
- `available_values_hint` is computed (`@api.depends('status_field_id', 'model_name')`) from the model's field definition — purely informational, helps admin see what values to enter in status_value_ids
- A rule is created when EITHER filter_mode != 'all' OR status filter is set — one line can have both independently
- `model_id` on `access.config.line` has `ondelete='cascade'` — deleting an ir.model cascades and deletes the line
- `status_field_id`, `access_id`, and `rule_id` all have `ondelete='set null'` — deletion of the referenced record nullifies the pointer without cascading
- The Config form includes an inline `alert-info` usage guide ("Necə işləyir?") visible to the admin
- In the config form's line list, the `user_field_id` column is hidden (`column_invisible`) when the parent config is in 'applied' state
