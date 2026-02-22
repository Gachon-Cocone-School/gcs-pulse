-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    google_sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(255),
    roles JSON DEFAULT '["user"]',
    league_type VARCHAR(32) NOT NULL DEFAULT 'none',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Terms table
CREATE TABLE IF NOT EXISTS terms (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'privacy' or 'tos'
    version VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _type_version_uc UNIQUE (type, version)
);

-- Consents table
CREATE TABLE IF NOT EXISTS consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    term_id INTEGER REFERENCES terms(id),
    agreed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _user_term_uc UNIQUE (user_id, term_id)
);

-- Route Permissions table (for RBAC & Default DISALLOW)
CREATE TABLE IF NOT EXISTS route_permissions (
    id SERIAL PRIMARY KEY,
    path VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    roles JSON DEFAULT '[]',
    CONSTRAINT _path_method_uc UNIQUE (path, method)
);

-- Role Assignment Rules table (for Dynamic Role Assignment)
CREATE TABLE IF NOT EXISTS role_assignment_rules (
    id SERIAL PRIMARY KEY,
    rule_type VARCHAR(50) NOT NULL, -- 'email_pattern' or 'email_list'
    rule_value JSON NOT NULL,      -- {"pattern": "..."} or {"emails": [...]}
    assigned_role VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    invite_code VARCHAR(64),
    league_type VARCHAR(32) NOT NULL DEFAULT 'none',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_teams_invite_code ON teams(invite_code);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

CREATE INDEX IF NOT EXISTS ix_users_team_id ON users(team_id);
CREATE INDEX IF NOT EXISTS ix_users_league_type ON users(league_type);
CREATE INDEX IF NOT EXISTS ix_teams_league_type ON teams(league_type);

CREATE TABLE IF NOT EXISTS daily_snippets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _user_date_uc UNIQUE (user_id, date)
);

CREATE TABLE IF NOT EXISTS weekly_snippets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    week DATE NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _user_week_uc UNIQUE (user_id, week)
);

CREATE INDEX IF NOT EXISTS ix_daily_snippets_user_id ON daily_snippets(user_id);
CREATE INDEX IF NOT EXISTS ix_daily_snippets_date ON daily_snippets(date);
CREATE INDEX IF NOT EXISTS ix_weekly_snippets_user_id ON weekly_snippets(user_id);
CREATE INDEX IF NOT EXISTS ix_weekly_snippets_week ON weekly_snippets(week);

CREATE TABLE IF NOT EXISTS achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    badge_image_url VARCHAR(2048) NOT NULL,
    rarity VARCHAR(16) NOT NULL DEFAULT 'common',
    is_public_announceable BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievement_grants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    achievement_definition_id INTEGER NOT NULL REFERENCES achievement_definitions(id),
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    publish_start_at TIMESTAMP WITH TIME ZONE NOT NULL,
    publish_end_at TIMESTAMP WITH TIME ZONE,
    external_grant_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_achievement_definitions_is_public_announceable ON achievement_definitions(is_public_announceable);
CREATE INDEX IF NOT EXISTS ix_achievement_grants_user_granted_at ON achievement_grants(user_id, granted_at DESC);
CREATE INDEX IF NOT EXISTS ix_achievement_grants_granted_at ON achievement_grants(granted_at DESC);
CREATE INDEX IF NOT EXISTS ix_achievement_grants_publish_window ON achievement_grants(publish_start_at, publish_end_at);
CREATE INDEX IF NOT EXISTS ix_achievement_grants_achievement_definition_id ON achievement_grants(achievement_definition_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_achievement_grants_external_grant_id
    ON achievement_grants(external_grant_id)
    WHERE external_grant_id IS NOT NULL;

-- Initial Data Seeding (Terms)
INSERT INTO terms (type, version, content, is_required, is_active) VALUES 
('privacy', 'v1.0', 'This is the privacy policy...', TRUE, TRUE),
('tos', 'v1.0', 'These are the terms of service...', TRUE, TRUE)
ON CONFLICT ON CONSTRAINT _type_version_uc DO NOTHING;
