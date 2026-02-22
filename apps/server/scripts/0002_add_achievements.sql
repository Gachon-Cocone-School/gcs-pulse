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

ALTER TABLE achievement_definitions
    ADD COLUMN IF NOT EXISTS rarity VARCHAR(16) NOT NULL DEFAULT 'common';

UPDATE achievement_definitions
SET rarity = 'common'
WHERE rarity IS NULL OR rarity = '';

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
