# Database

This repository uses **PostgreSQL** (async access via `asyncpg` + SQLAlchemy 2.x).

This document is based on a live schema introspection of the DB specified by `DATABASE_URL` in `.env`.

> Security note: do not paste `DATABASE_URL` values (it contains credentials) into issues/PRs/logs.

## High-level

The connected database appears to be a **Supabase Postgres** instance.

Schemas and table counts observed:

- `public`: 5 tables (**this service’s tables**)
- `auth`: 20 tables (Supabase Auth internal)
- `storage`: 9 tables (Supabase Storage internal)
- `realtime`: 3 tables (Supabase Realtime internal)
- `vault`: 1 table (Supabase Vault internal)

This service primarily owns and uses the `public.*` tables listed below.

## How schema is managed in this repo

Sources of truth:

- **SQLAlchemy models**: `app/models.py`
- **Bootstrap DDL** (reference): `scripts/init_db.sql`
- **Migration / sync script**: `scripts/migrate_and_seed.py`
  - Ensures required columns exist (example: `users.roles`)
  - Runs `Base.metadata.create_all()`
  - Syncs FastAPI routes into `public.route_permissions` (Default DISALLOW RBAC)

When you add a new endpoint, you usually must run:

```bash
python scripts/migrate_and_seed.py
```

## Service tables (schema: `public`)

### `public.users`

OAuth user registry. Roles are stored as JSON.

Columns:

- `id` `integer` (PK, sequence `users_id_seq`) **NOT NULL**
- `email` `varchar` **NOT NULL**
- `name` `varchar` NULL
- `picture` `varchar` NULL
- `created_at` `timestamptz` NULL default `now()`
- `roles` `json` NULL (expected default set by migration script / model)

Indexes:

- `users_pkey` UNIQUE BTREE (`id`)
- `ix_users_id` BTREE (`id`)
- `ix_users_email` UNIQUE BTREE (`email`)

Related code:

- Model: `app/models.py:User`
- CRUD: `app/crud.py:create_or_update_user`, `app/crud.py:get_user_by_email`

---

### `public.terms`

Terms of service definitions (type/version/content). Supports required/active flags.

Columns:

- `id` `integer` (PK, sequence `terms_id_seq`) **NOT NULL**
- `type` `varchar` **NOT NULL**
- `version` `varchar` **NOT NULL**
- `content` `text` **NOT NULL**
- `is_required` `bool` NULL
- `is_active` `bool` NULL
- `created_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `terms_pkey` UNIQUE BTREE (`id`)
- `ix_terms_id` BTREE (`id`)
- `_type_version_uc` UNIQUE BTREE (`type`, `version`) (also present as a constraint)

Related code:

- Model: `app/models.py:Term`
- Router: `app/routers/terms.py`, `app/routers/admin.py` (admin CRUD)

---

### `public.consents`

User consent records for terms.

Columns:

- `id` `integer` (PK, sequence `consents_id_seq`) **NOT NULL**
- `user_id` `int4` NULL → FK to `public.users(id)`
- `term_id` `int4` NULL → FK to `public.terms(id)`
- `agreed_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `consents_pkey` UNIQUE BTREE (`id`)
- `ix_consents_id` BTREE (`id`)
- `_user_term_uc` UNIQUE BTREE (`user_id`, `term_id`) (also present as a constraint)
- FKs:
  - `consents_user_id_fkey` (`user_id`) → `public.users(id)`
  - `consents_term_id_fkey` (`term_id`) → `public.terms(id)`

Related code:

- Model: `app/models.py:Consent`
- Dependency enforcement: `app/dependencies.py:get_active_user` (checks required active terms)

---

### `public.teams`

Users can optionally belong to a single team.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `name` `varchar` **NOT NULL**
- `created_at` `timestamptz` NULL default `now()`

Indexes:

- `teams_pkey` UNIQUE BTREE (`id`)
- `ix_teams_id` BTREE (`id`)

Related code:

- Model: `app/models.py:Team`
- Router: `app/routers/teams.py` (Admin only)

---

### `public.daily_snippets`

Daily work snippets. One per user per business day (09:00 cutoff).

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `public.users(id)`
- `date` `date` **NOT NULL**
- `content` `text` **NOT NULL**
- `structured` `text` NULL
- `playbook` `text` NULL
- `feedback` `text` NULL
- `created_at` `timestamptz` NULL default `now()`
- `updated_at` `timestamptz` NULL default `now()`

Constraints / Indexes:

- `daily_snippets_pkey` UNIQUE BTREE (`id`)
- `ix_daily_snippets_id` BTREE (`id`)
- `ix_daily_snippets_user_id` BTREE (`user_id`)
- `ix_daily_snippets_date` BTREE (`date`)
- `_user_date_uc` UNIQUE (`user_id`, `date`)

Related code:

- Model: `app/models.py:DailySnippet`
- Router: `app/routers/daily_snippets.py`

---

### `public.weekly_snippets`

Weekly work snippets. One per user per business week (Monday 09:00 cutoff).

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `public.users(id)`
- `week` `date` **NOT NULL** (Monday date)
- `content` `text` **NOT NULL**
- `structured` `text` NULL
- `playbook` `text` NULL
- `feedback` `text` NULL
- `created_at` `timestamptz` NULL default `now()`
- `updated_at` `timestamptz` NULL default `now()`

Constraints / Indexes:

- `weekly_snippets_pkey` UNIQUE BTREE (`id`)
- `ix_weekly_snippets_id` BTREE (`id`)
- `ix_weekly_snippets_user_id` BTREE (`user_id`)
- `ix_weekly_snippets_week` BTREE (`week`)
- `_user_week_uc` UNIQUE (`user_id`, `week`)

Related code:

- Model: `app/models.py:WeeklySnippet`
- Router: `app/routers/weekly_snippets.py`

---

### `public.route_permissions`

Default DISALLOW RBAC rules: permission rows are per **FastAPI route template path** + HTTP method.

Columns:

- `id` `integer` (PK, sequence `route_permissions_id_seq`) **NOT NULL**
- `path` `varchar` **NOT NULL**
- `method` `varchar` **NOT NULL**
- `is_public` `bool` NULL
- `roles` `json` NULL

Constraints / indexes:

- `route_permissions_pkey` UNIQUE BTREE (`id`)
- `ix_route_permissions_id` BTREE (`id`)
- `_path_method_uc` UNIQUE BTREE (`path`, `method`) (also present as a constraint)

Related code:

- Model: `app/models.py:RoutePermission`
- Enforced by: `app/dependencies.py:check_route_permissions`
- Synced by: `scripts/migrate_and_seed.py`

Important behavior:

- If no row exists for `(path, method)`, access is denied (`403`).
- Public endpoints must be explicitly marked `is_public=true`.
- Non-public endpoints require session auth + role intersection.

---

### `public.role_assignment_rules`

Auto role assignment rules applied on login.

Columns:

- `id` `integer` (PK, sequence `role_assignment_rules_id_seq`) **NOT NULL**
- `rule_type` `varchar` **NOT NULL** (e.g. `email_pattern` / `email_list`)
- `rule_value` `json` **NOT NULL** (e.g. `{ "pattern": "%@example.com" }` or `{ "emails": ["a@b.com"] }`)
- `assigned_role` `varchar` **NOT NULL**
- `priority` `int4` NULL
- `is_active` `bool` NULL
- `created_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `role_assignment_rules_pkey` UNIQUE BTREE (`id`)
- `ix_role_assignment_rules_id` BTREE (`id`)

Related code:

- Model: `app/models.py:RoleAssignmentRule`
- Rule application: `app/crud.py:apply_role_rules`
- Login flow: `app/routers/auth.py:auth_callback`

## Notes / Caveats

- The database contains many non-`public` tables belonging to Supabase (`auth`, `storage`, `realtime`, `vault`). This service should generally avoid touching those schemas directly.
- Some constraints show up as platform-generated NOT NULL checks (`2200_*_not_null`). These are internal representations of NOT NULL constraints in Postgres catalogs.
