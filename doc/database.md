# Database

This service uses SQLAlchemy 2.x async engine and supports environment-based database backends:

- `production`: `DATABASE_URL`
- `test`: `TEST_DATABASE_URL` (if provided)
- otherwise (`development`): `DEV_DATABASE_URL`

Default URLs in config are SQLite (`sqlite+aiosqlite`), but Postgres DSNs are also supported.

## High-level

The application schema is defined by SQLAlchemy models and synced by migration scripts.
Current server code defines **12 service tables**:

- `users`
- `terms`
- `consents`
- `route_permissions`
- `role_assignment_rules`
- `teams`
- `daily_snippets`
- `weekly_snippets`
- `api_tokens`
- `comments`
- `achievement_definitions`
- `achievement_grants`

## How schema is managed in this repo

Sources of truth:

- **SQLAlchemy models**: `apps/server/app/models.py`
- **Bootstrap DDL (reference)**: `apps/server/scripts/init_db.sql`
- **Migration / sync script**: `apps/server/scripts/migrate_and_seed.py`
  - Runs `Base.metadata.create_all()`
  - Ensures additive columns/indexes exist (e.g. `users.roles`, `teams.invite_code`, snippet indexes)
  - Syncs FastAPI routes into `route_permissions`

Typical sync command:

```bash
python apps/server/scripts/migrate_and_seed.py
```

## Service tables (schema: `public`)

### `users`

OAuth user registry. Roles are stored as JSON.

Columns:

- `id` `integer` (PK, sequence `users_id_seq`) **NOT NULL**
- `email` `varchar` **NOT NULL**
- `name` `varchar` NULL
- `picture` `varchar` NULL
- `created_at` `timestamptz` NULL default `now()`
- `roles` `json` NULL default `['user']`
- `league_type` `varchar` **NOT NULL** default `'none'`
- `team_id` `integer` NULL → FK to `teams(id)`

Indexes:

- `users_pkey` UNIQUE BTREE (`id`)
- `ix_users_id` BTREE (`id`)
- `ix_users_email` UNIQUE BTREE (`email`)
- `ix_users_team_id` BTREE (`team_id`)
- `ix_users_league_type` BTREE (`league_type`)

Related code:

- Model: `apps/server/app/models.py:User`
- CRUD: `apps/server/app/crud.py:create_or_update_user`, `apps/server/app/crud.py:get_user_by_email`

---

### `terms`

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

- Model: `apps/server/app/models.py:Term`
- Router: `apps/server/app/routers/terms.py`, `apps/server/app/routers/admin.py` (admin CRUD)

---

### `consents`

User consent records for terms.

Columns:

- `id` `integer` (PK, sequence `consents_id_seq`) **NOT NULL**
- `user_id` `int4` NULL → FK to `users(id)`
- `term_id` `int4` NULL → FK to `terms(id)`
- `agreed_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `consents_pkey` UNIQUE BTREE (`id`)
- `ix_consents_id` BTREE (`id`)
- `_user_term_uc` UNIQUE BTREE (`user_id`, `term_id`) (also present as a constraint)
- FKs:
  - `consents_user_id_fkey` (`user_id`) → `users(id)`
  - `consents_term_id_fkey` (`term_id`) → `terms(id)`

Related code:

- Model: `apps/server/app/models.py:Consent`
- Dependency enforcement: `apps/server/app/dependencies.py:get_active_user` (checks required active terms)

---

### `teams`

Users can optionally belong to a single team.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `name` `varchar` **NOT NULL**
- `invite_code` `varchar` NULL (unique)
- `league_type` `varchar` **NOT NULL** default `'none'`
- `created_at` `timestamptz` NULL default `now()`

Indexes:

- `teams_pkey` UNIQUE BTREE (`id`)
- `ix_teams_id` BTREE (`id`)
- `ux_teams_invite_code` UNIQUE BTREE (`invite_code`)
- `ix_teams_league_type` BTREE (`league_type`)

Related code:

- Model: `apps/server/app/models.py:Team`
- Router: `apps/server/app/routers/teams.py`

---

### `daily_snippets`

Daily work snippets. One per user per business day (09:00 cutoff).

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `users(id)`
- `date` `date` **NOT NULL**
- `content` `text` **NOT NULL**
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

- Model: `apps/server/app/models.py:DailySnippet`
- Router: `apps/server/app/routers/daily_snippets.py`

---

### `weekly_snippets`

Weekly work snippets. One per user per business week (Monday 09:00 cutoff).

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `users(id)`
- `week` `date` **NOT NULL** (Monday date)
- `content` `text` **NOT NULL**
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

- Model: `apps/server/app/models.py:WeeklySnippet`
- Router: `apps/server/app/routers/weekly_snippets.py`

---

### `route_permissions`

Route permission metadata table (synced by migration script from FastAPI routes).

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

- Model: `apps/server/app/models.py:RoutePermission`
- Synced by: `apps/server/scripts/migrate_and_seed.py`

---

### `role_assignment_rules`

Role assignment rule definitions used by admin/sync workflows.

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

- Model: `apps/server/app/models.py:RoleAssignmentRule`
- Seed/sync: `apps/server/scripts/migrate_and_seed.py`
- Referenced schema type: `apps/server/app/schemas.py` (`RuleType`)

### `api_tokens`

Personal API token table for Bearer authentication.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `users(id)`
- `token_hash` `varchar` **NOT NULL** (unique)
- `description` `varchar` NULL
- `idempotency_key` `varchar` NULL
- `created_at` `timestamptz` NULL default `now()`
- `last_used_at` `timestamptz` NULL

Constraints / indexes:

- `api_tokens_pkey` UNIQUE BTREE (`id`)
- `ix_api_tokens_id` BTREE (`id`)
- `ix_api_tokens_user_id` BTREE (`user_id`)
- `ix_api_tokens_token_hash` UNIQUE BTREE (`token_hash`)
- `ux_api_token_user_id_idempotency_key` UNIQUE (`user_id`, `idempotency_key`)

Related code:

- Model: `apps/server/app/models.py:ApiToken`
- SQL migration: `apps/server/scripts/0001_add_idempotency_key.sql`

---

### `comments`

Comment table for daily/weekly snippets.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `users(id)`
- `daily_snippet_id` `integer` NULL → FK to `daily_snippets(id)`
- `weekly_snippet_id` `integer` NULL → FK to `weekly_snippets(id)`
- `content` `text` **NOT NULL**
- `created_at` `timestamptz` NULL default `now()`
- `updated_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `comments_pkey` UNIQUE BTREE (`id`)
- `ix_comments_id` BTREE (`id`)
- `ix_comments_user_id` BTREE (`user_id`)
- `ix_comments_daily_snippet_id` BTREE (`daily_snippet_id`)
- `ix_comments_weekly_snippet_id` BTREE (`weekly_snippet_id`)

Related code:

- Model: `apps/server/app/models.py:Comment`

---

### `achievement_definitions`

Achievement metadata definitions.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `code` `varchar` **NOT NULL** (unique)
- `name` `varchar` **NOT NULL**
- `description` `text` **NOT NULL**
- `badge_image_url` `varchar` **NOT NULL**
- `rarity` `varchar(16)` **NOT NULL** default `'common'`
- `is_public_announceable` `bool` **NOT NULL** default `false`
- `created_at` `timestamptz` NULL default `now()`
- `updated_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `achievement_definitions_pkey` UNIQUE BTREE (`id`)
- `ix_achievement_definitions_id` BTREE (`id`)
- `ix_achievement_definitions_code` UNIQUE BTREE (`code`)
- `ix_achievement_definitions_is_public_announceable` BTREE (`is_public_announceable`)

Related code:

- Model: `apps/server/app/models.py:AchievementDefinition`
- SQL migration: `apps/server/scripts/0002_add_achievements.sql`

---

### `achievement_grants`

Granted achievement events per user.

Columns:

- `id` `integer` (PK) **NOT NULL**
- `user_id` `integer` **NOT NULL** → FK to `users(id)`
- `achievement_definition_id` `integer` **NOT NULL** → FK to `achievement_definitions(id)`
- `granted_at` `timestamptz` **NOT NULL**
- `publish_start_at` `timestamptz` **NOT NULL**
- `publish_end_at` `timestamptz` NULL
- `external_grant_id` `varchar` NULL
- `created_at` `timestamptz` NULL default `now()`

Constraints / indexes:

- `achievement_grants_pkey` UNIQUE BTREE (`id`)
- `ix_achievement_grants_id` BTREE (`id`)
- `ix_achievement_grants_user_id` BTREE (`user_id`)
- `ix_achievement_grants_achievement_definition_id` BTREE (`achievement_definition_id`)
- `ix_achievement_grants_granted_at` BTREE (`granted_at`)
- `ix_achievement_grants_publish_start_at` BTREE (`publish_start_at`)
- `ix_achievement_grants_publish_end_at` BTREE (`publish_end_at`)
- `ix_achievement_grants_publish_window` BTREE (`publish_start_at`, `publish_end_at`)
- `ix_achievement_grants_user_granted_at` BTREE (`user_id`, `granted_at DESC`)
- `ix_achievement_grants_external_grant_id` UNIQUE BTREE (`external_grant_id`) WHERE `external_grant_id IS NOT NULL`

Related code:

- Model: `apps/server/app/models.py:AchievementGrant`
- SQL migration: `apps/server/scripts/0002_add_achievements.sql`

## Notes / Caveats

- For this repository, treat server model definitions as canonical source of table/column shape.
- `apps/server/scripts/init_db.sql` and `apps/server/scripts/migrate_and_seed.py` are additive sync/bootstrap utilities and may include compatibility logic over time.
