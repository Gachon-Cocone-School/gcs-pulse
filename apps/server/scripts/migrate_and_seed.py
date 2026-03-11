import asyncio
import sys
import os
import secrets
import string

# Add project root to path
sys.path.append(os.getcwd())


ROLE_EMAIL_LISTS = {
    "gcs": ["namjookim@gachon.ac.kr"],
    "교수": ["namjookim@gachon.ac.kr"],
    "admin": ["namjookim@gachon.ac.kr"],
}

E2E_BYPASS_EMAIL = os.getenv("TEST_AUTH_BYPASS_EMAIL")
if E2E_BYPASS_EMAIL:
    normalized_e2e_email = E2E_BYPASS_EMAIL.strip().lower()
    if normalized_e2e_email:
        for role_key in ("가천대학교", "gcs", "교수"):
            current_emails = ROLE_EMAIL_LISTS.setdefault(role_key, [])
            if normalized_e2e_email not in current_emails:
                current_emails.append(normalized_e2e_email)

from sqlalchemy import text
from app import crud, crud_users
from app.achievement_rules import ACHIEVEMENT_DEFINITIONS
from app.database import engine, Base
from app.models import RoutePermission, RoleAssignmentRule, User
from app.main import app
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


def _generate_invite_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def migrate_and_seed():
    async with engine.begin() as conn:
        print("Ensuring tables and columns exist...")

        # Create ORM tables first so dialect-specific PK/identity behavior is correct
        await conn.run_sync(Base.metadata.create_all)
        print("  - Base metadata tables created/verified.")

        try:
            drop_risk_snapshot_sql = "DROP TABLE IF EXISTS student_risk_snapshots"
            if conn.dialect.name == "postgresql":
                drop_risk_snapshot_sql += " CASCADE"
            await conn.execute(text(drop_risk_snapshot_sql))
            print("  - student_risk_snapshots dropped (if existed).")
        except Exception as e:
            print(f"  - Skipping student_risk_snapshots drop: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS achievement_definitions ("
                    "id SERIAL PRIMARY KEY, "
                    "code VARCHAR(255) UNIQUE NOT NULL, "
                    "name VARCHAR(255) NOT NULL, "
                    "description TEXT NOT NULL, "
                    "badge_image_url VARCHAR(2048) NOT NULL, "
                    "rarity VARCHAR(16) NOT NULL DEFAULT 'common', "
                    "is_public_announceable BOOLEAN NOT NULL DEFAULT FALSE, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS achievement_grants ("
                    "id SERIAL PRIMARY KEY, "
                    "user_id INTEGER NOT NULL REFERENCES users(id), "
                    "achievement_definition_id INTEGER NOT NULL REFERENCES achievement_definitions(id), "
                    "granted_at TIMESTAMP WITH TIME ZONE NOT NULL, "
                    "publish_start_at TIMESTAMP WITH TIME ZONE NOT NULL, "
                    "publish_end_at TIMESTAMP WITH TIME ZONE, "
                    "external_grant_id VARCHAR(255), "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_achievement_definitions_is_public_announceable ON achievement_definitions(is_public_announceable)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_achievement_grants_user_granted_at ON achievement_grants(user_id, granted_at DESC)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_achievement_grants_granted_at ON achievement_grants(granted_at DESC)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_achievement_grants_publish_window ON achievement_grants(publish_start_at, publish_end_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_achievement_grants_achievement_definition_id ON achievement_grants(achievement_definition_id)"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_achievement_grants_external_grant_id "
                    "ON achievement_grants(external_grant_id) "
                    "WHERE external_grant_id IS NOT NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE achievement_definitions "
                    "ADD COLUMN IF NOT EXISTS rarity VARCHAR(16) NOT NULL DEFAULT 'common'"
                )
            )
            await conn.execute(
                text(
                    "UPDATE achievement_definitions "
                    "SET rarity = 'common' "
                    "WHERE rarity IS NULL OR rarity = ''"
                )
            )
        except Exception as e:
            print(f"  - Skipping achievement schema migration: {e}")

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS roles JSON DEFAULT '[\"user\"]'"
                )
            )
        except Exception as e:
            print(f"  - Skipping users.roles migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS google_sub"))
            print("  - users.google_sub dropped (if existed).")
        except Exception as e:
            print(f"  - Skipping users.google_sub drop: {e}")

        try:
            await conn.execute(text("ALTER TABLE users ALTER COLUMN email SET NOT NULL"))
        except Exception as e:
            print(f"  - Skipping users.email NOT NULL migration: {e}")

        try:
            await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
        except Exception as e:
            print(f"  - Skipping users.email unique index creation: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS teams ("
                    "id SERIAL PRIMARY KEY, "
                    "name VARCHAR(255) NOT NULL, "
                    "invite_code VARCHAR(64), "
                    "league_type VARCHAR(32) NOT NULL DEFAULT 'none', "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
        except Exception as e:
            print(f"  - Skipping teams table creation: {e}")

        try:
            await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS invite_code VARCHAR(64)"))
        except Exception as e:
            print(f"  - Skipping teams.invite_code migration: {e}")

        try:
            await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_teams_invite_code ON teams(invite_code)"))
        except Exception as e:
            print(f"  - Skipping teams invite_code index creation: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS peer_evaluation_sessions ("
                    "id SERIAL PRIMARY KEY, "
                    "title VARCHAR(255) NOT NULL, "
                    "professor_user_id INTEGER NOT NULL REFERENCES users(id), "
                    "is_open BOOLEAN NOT NULL DEFAULT TRUE, "
                    "access_token VARCHAR(128) NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(text("ALTER TABLE peer_evaluation_sessions DROP COLUMN IF EXISTS project_name"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_evaluation_sessions_access_token "
                    "ON peer_evaluation_sessions(access_token)"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS peer_evaluation_session_members ("
                    "id SERIAL PRIMARY KEY, "
                    "session_id INTEGER NOT NULL REFERENCES peer_evaluation_sessions(id), "
                    "student_user_id INTEGER NOT NULL REFERENCES users(id), "
                    "team_label VARCHAR(64) NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_eval_session_member_session_student "
                    "ON peer_evaluation_session_members(session_id, student_user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_peer_eval_session_members_session_team "
                    "ON peer_evaluation_session_members(session_id, team_label)"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS peer_evaluation_submissions ("
                    "id SERIAL PRIMARY KEY, "
                    "session_id INTEGER NOT NULL REFERENCES peer_evaluation_sessions(id), "
                    "evaluator_user_id INTEGER NOT NULL REFERENCES users(id), "
                    "evaluatee_user_id INTEGER NOT NULL REFERENCES users(id), "
                    "contribution_percent INTEGER NOT NULL, "
                    "fit_yes_no BOOLEAN NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_eval_submission_session_evaluator_evaluatee "
                    "ON peer_evaluation_submissions(session_id, evaluator_user_id, evaluatee_user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_peer_eval_submission_session_evaluator "
                    "ON peer_evaluation_submissions(session_id, evaluator_user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_peer_eval_submission_session_evaluatee "
                    "ON peer_evaluation_submissions(session_id, evaluatee_user_id)"
                )
            )
        except Exception as e:
            print(f"  - Skipping peer_evaluation schema migration: {e}")

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)"
                )
            )
        except Exception as e:
            print(f"  - Skipping users.team_id migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS league_type VARCHAR(32) DEFAULT 'none'"))
        except Exception as e:
            print(f"  - Skipping users.league_type migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS league_type VARCHAR(32) DEFAULT 'none'"))
        except Exception as e:
            print(f"  - Skipping teams.league_type migration: {e}")

        try:
            await conn.execute(text("UPDATE users SET league_type = 'none' WHERE league_type IS NULL"))
            await conn.execute(text("UPDATE teams SET league_type = 'none' WHERE league_type IS NULL"))
        except Exception as e:
            print(f"  - Skipping league_type backfill: {e}")

        try:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_league_type ON users(league_type)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_league_type ON teams(league_type)"))
        except Exception as e:
            print(f"  - Skipping league_type index creation: {e}")

        try:
            await conn.execute(text("ALTER TABLE daily_snippets ADD COLUMN IF NOT EXISTS playbook TEXT"))
        except Exception as e:
            print(f"  - Skipping daily_snippets.playbook migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE daily_snippets ADD COLUMN IF NOT EXISTS feedback TEXT"))
        except Exception as e:
            print(f"  - Skipping daily_snippets.feedback migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE weekly_snippets ADD COLUMN IF NOT EXISTS playbook TEXT"))
        except Exception as e:
            print(f"  - Skipping weekly_snippets.playbook migration: {e}")

        try:
            await conn.execute(text("ALTER TABLE weekly_snippets ADD COLUMN IF NOT EXISTS feedback TEXT"))
        except Exception as e:
            print(f"  - Skipping weekly_snippets.feedback migration: {e}")

        try:
            await conn.execute(
                text(
                    "ALTER TABLE comments "
                    "ADD COLUMN IF NOT EXISTS comment_type VARCHAR(16) NOT NULL DEFAULT 'peer'"
                )
            )
            await conn.execute(
                text(
                    "UPDATE comments "
                    "SET comment_type = 'peer' "
                    "WHERE comment_type IS NULL OR comment_type = ''"
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_comment_type ON comments(comment_type)"))
        except Exception as e:
            print(f"  - Skipping comments.comment_type migration: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_daily_snippets_user_id ON daily_snippets(user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_daily_snippets_date ON daily_snippets(date)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_weekly_snippets_user_id ON weekly_snippets(user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_weekly_snippets_week ON weekly_snippets(week)"
                )
            )
        except Exception as e:
            print(f"  - Skipping snippet index creation: {e}")

        try:
            result = await conn.execute(text("SELECT id FROM teams WHERE invite_code IS NULL OR invite_code = ''"))
            team_ids = [row[0] for row in result.fetchall()]
            for team_id in team_ids:
                while True:
                    code = _generate_invite_code()
                    exists = await conn.execute(
                        text("SELECT 1 FROM teams WHERE invite_code = :invite_code LIMIT 1"),
                        {"invite_code": code},
                    )
                    if exists.first() is None:
                        break
                await conn.execute(
                    text("UPDATE teams SET invite_code = :invite_code WHERE id = :team_id"),
                    {"invite_code": code, "team_id": team_id},
                )
        except Exception as e:
            print(f"  - Skipping teams invite_code backfill: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS notifications ("
                    "id SERIAL PRIMARY KEY, "
                    "user_id INTEGER NOT NULL REFERENCES users(id), "
                    "actor_user_id INTEGER NOT NULL REFERENCES users(id), "
                    "type VARCHAR(50) NOT NULL, "
                    "daily_snippet_id INTEGER REFERENCES daily_snippets(id), "
                    "weekly_snippet_id INTEGER REFERENCES weekly_snippets(id), "
                    "comment_id INTEGER REFERENCES comments(id), "
                    "is_read BOOLEAN NOT NULL DEFAULT FALSE, "
                    "read_at TIMESTAMP WITH TIME ZONE, "
                    "dedupe_key VARCHAR(255) NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS notification_settings ("
                    "user_id INTEGER PRIMARY KEY REFERENCES users(id), "
                    "notify_post_author BOOLEAN NOT NULL DEFAULT TRUE, "
                    "notify_mentions BOOLEAN NOT NULL DEFAULT TRUE, "
                    "notify_participants BOOLEAN NOT NULL DEFAULT TRUE, "
                    "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )

            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS actor_user_id INTEGER REFERENCES users(id)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS type VARCHAR(50)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS daily_snippet_id INTEGER REFERENCES daily_snippets(id)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS weekly_snippet_id INTEGER REFERENCES weekly_snippets(id)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS comment_id INTEGER REFERENCES comments(id)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(255)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notifications "
                    "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )
            )

            await conn.execute(
                text(
                    "ALTER TABLE notification_settings "
                    "ADD COLUMN IF NOT EXISTS notify_post_author BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notification_settings "
                    "ADD COLUMN IF NOT EXISTS notify_mentions BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notification_settings "
                    "ADD COLUMN IF NOT EXISTS notify_participants BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notification_settings "
                    "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE notification_settings "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO notification_settings (user_id) "
                    "SELECT id FROM users "
                    "ON CONFLICT(user_id) DO NOTHING"
                )
            )

            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_user_created_at "
                    "ON notifications(user_id, created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_user_id_is_read_created_at "
                    "ON notifications(user_id, is_read, created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_type_created_at "
                    "ON notifications(type, created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_daily_snippet_id "
                    "ON notifications(daily_snippet_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_weekly_snippet_id "
                    "ON notifications(weekly_snippet_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_comment_id "
                    "ON notifications(comment_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_notifications_actor_user_id "
                    "ON notifications(actor_user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_notifications_dedupe_key "
                    "ON notifications(dedupe_key)"
                )
            )
        except Exception as e:
            print(f"  - Skipping notification schema migration: {e}")

        try:
            # Keep required terms active and up-to-date.
            await conn.execute(
                text(
                    "INSERT INTO terms (type, version, content, is_required, is_active) VALUES "
                    "('privacy', 'v1.0', 'This is the privacy policy...', TRUE, TRUE), "
                    "('tos', 'v1.0', 'These are the terms of service...', TRUE, TRUE) "
                    "ON CONFLICT(type, version) DO UPDATE SET "
                    "content = EXCLUDED.content, "
                    "is_required = EXCLUDED.is_required, "
                    "is_active = EXCLUDED.is_active"
                )
            )

            # Auto-pass required terms for all existing users.
            await conn.execute(
                text(
                    "INSERT INTO consents (user_id, term_id) "
                    "SELECT u.id, t.id "
                    "FROM users u "
                    "JOIN terms t ON t.is_active = TRUE AND t.is_required = TRUE "
                    "ON CONFLICT(user_id, term_id) DO NOTHING"
                )
            )
            print("  - Required terms seeded and consents backfilled for all users.")
        except Exception as e:
            print(f"  - Skipping terms/consents seed: {e}")

    async with AsyncSessionLocal() as session:
        # 3. Sync Routes from FastAPI App
        print("Syncing routes from FastAPI app to route_permissions table...")

        # Define security rules
        # (path_pattern, method) -> (is_public, [roles])
        privileged_roles = ["gcs", "교수", "admin"]
        login_only_roles = ["가천대학교"]
        special_rules = {
            ("/auth/google/login", "GET"): (True, []),
            ("/auth/google/callback", "GET"): (True, []),
            ("/auth/logout", "POST"): (False, privileged_roles),
            ("/docs", "GET"): (True, []),
            ("/openapi.json", "GET"): (True, []),
            ("/redoc", "GET"): (True, []),
            ("/docs/oauth2-redirect", "GET"): (True, []),
            ("/terms", "GET"): (True, []),
            ("/auth/me", "GET"): (False, privileged_roles + login_only_roles),
            ("/notification/public/sse", "GET"): (True, []),
        }

        seen_route_keys = set()

        for route in app.routes:
            if not (hasattr(route, "path") and hasattr(route, "methods")):
                continue

            path = route.path
            for method in route.methods:
                # Default security: Private, privileged roles allowed
                is_public = False
                allowed_roles = privileged_roles

                # Apply rules
                if (path, method) in special_rules:
                    is_public, allowed_roles = special_rules[(path, method)]
                elif path.startswith("/admin"):
                    is_public = False
                    allowed_roles = privileged_roles
                elif method == "HEAD":
                    # Copy from GET if available
                    if (path, "GET") in special_rules:
                        is_public, allowed_roles = special_rules[(path, "GET")]
                    else:
                        is_public = False
                        allowed_roles = privileged_roles

                route_key = (path, method)
                seen_route_keys.add(route_key)

                # Check if exists
                result = await session.execute(
                    select(RoutePermission).filter(
                        RoutePermission.path == path, RoutePermission.method == method
                    )
                )
                db_perm = result.scalars().first()

                if not db_perm:
                    print(f"  + Adding {method} {path}")
                    db_perm = RoutePermission(
                        path=path,
                        method=method,
                        is_public=is_public,
                        roles=allowed_roles,
                    )
                    session.add(db_perm)
                else:
                    # Update existing for consistency
                    db_perm.is_public = is_public
                    db_perm.roles = allowed_roles

        # Ensure explicit special rules are synced even if route is not in app.routes
        for (path, method), (is_public, allowed_roles) in special_rules.items():
            if (path, method) in seen_route_keys:
                continue

            result = await session.execute(
                select(RoutePermission).filter(
                    RoutePermission.path == path, RoutePermission.method == method
                )
            )
            db_perm = result.scalars().first()

            if not db_perm:
                print(f"  + Adding {method} {path} (special rule)")
                db_perm = RoutePermission(
                    path=path,
                    method=method,
                    is_public=is_public,
                    roles=allowed_roles,
                )
                session.add(db_perm)
            else:
                db_perm.is_public = is_public
                db_perm.roles = allowed_roles

        print("Seeding role_assignment_rules...")

        rule_priority = {
            "admin": 10,
            "gcs": 20,
            "교수": 30,
            "가천대학교": 100,
        }

        role_rules = [
            {
                "rule_type": "email_list",
                "rule_value": {"emails": emails},
                "assigned_role": role,
                "priority": rule_priority[role],
                "is_active": True,
            }
            for role, emails in ROLE_EMAIL_LISTS.items()
        ]
        role_rules.append(
            {
                "rule_type": "email_pattern",
                "rule_value": {"pattern": "%@gachon.ac.kr"},
                "assigned_role": "가천대학교",
                "priority": rule_priority["가천대학교"],
                "is_active": True,
            }
        )

        for rule in role_rules:
            result = await session.execute(
                select(RoleAssignmentRule).filter(
                    RoleAssignmentRule.rule_type == rule["rule_type"],
                    RoleAssignmentRule.assigned_role == rule["assigned_role"],
                )
            )
            existing_rule = result.scalars().first()

            if not existing_rule:
                session.add(RoleAssignmentRule(**rule))
                continue

            existing_rule.rule_value = rule["rule_value"]
            existing_rule.priority = rule["priority"]
            existing_rule.is_active = rule["is_active"]

        print("Syncing achievement definitions from achievement rules...")
        await crud.upsert_achievement_definitions(
            session,
            ACHIEVEMENT_DEFINITIONS,
            commit=False,
        )

        print("Backfilling user roles from role_assignment_rules...")
        rules_result = await session.execute(
            select(RoleAssignmentRule)
            .filter(RoleAssignmentRule.is_active.is_(True))
            .order_by(RoleAssignmentRule.priority.asc(), RoleAssignmentRule.id.asc())
        )
        active_rules = rules_result.scalars().all()

        users_result = await session.execute(select(User))
        all_users = users_result.scalars().all()

        for user in all_users:
            email = (user.email or "").strip().lower()
            user.roles = (
                crud_users._resolve_roles_from_rules(email, active_rules)
                if email
                else ["user"]
            )

        await session.commit()
        print("Sync and Seeding Complete.")


if __name__ == "__main__":
    asyncio.run(migrate_and_seed())
