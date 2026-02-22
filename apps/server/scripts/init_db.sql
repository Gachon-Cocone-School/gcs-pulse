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

-- Initial Data Seeding (Terms)
INSERT INTO terms (type, version, content, is_required, is_active) VALUES 
('privacy', 'v1.0', 'This is the privacy policy...', TRUE, TRUE),
('tos', 'v1.0', 'These are the terms of service...', TRUE, TRUE)
ON CONFLICT ON CONSTRAINT _type_version_uc DO NOTHING;
