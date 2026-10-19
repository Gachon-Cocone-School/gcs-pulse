-- A/B 실습 전용 신규 테이블 및 route_permissions 행 추가 스크립트
-- Supabase PostgreSQL용. 기존 테이블/컬럼/행은 수정하거나 삭제하지 않습니다.
-- 이미 존재하는 같은 경로/메서드 권한 행은 그대로 보존합니다.
-- Supabase SQL Editor에서 수동 실행할 수 있습니다.

BEGIN;

CREATE TABLE IF NOT EXISTS public.ab_practice_sessions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    professor_user_id INTEGER NOT NULL REFERENCES public.users(id),
    access_token VARCHAR(128) NOT NULL,
    question VARCHAR(500) NOT NULL DEFAULT 'A/B 중 어느게 좋나요?',
    exposure_seconds INTEGER NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'setup',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_sessions_id
    ON public.ab_practice_sessions (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_sessions_professor_user_id
    ON public.ab_practice_sessions (professor_user_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_sessions_status
    ON public.ab_practice_sessions (status);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ab_practice_sessions_access_token
    ON public.ab_practice_sessions (access_token);

CREATE TABLE IF NOT EXISTS public.ab_practice_members (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES public.ab_practice_sessions(id),
    student_user_id INTEGER NOT NULL REFERENCES public.users(id),
    team_label VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_ab_practice_member_session_student
        UNIQUE (session_id, student_user_id)
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_members_id
    ON public.ab_practice_members (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_members_session_id
    ON public.ab_practice_members (session_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_members_student_user_id
    ON public.ab_practice_members (student_user_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_members_session_team
    ON public.ab_practice_members (session_id, team_label);

CREATE TABLE IF NOT EXISTS public.ab_practice_pairs (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES public.ab_practice_sessions(id),
    title VARCHAR(200) NOT NULL DEFAULT '',
    team_label VARCHAR(64) NOT NULL,
    slot_number INTEGER NOT NULL,
    image_a_path VARCHAR(500),
    image_b_path VARCHAR(500),
    created_by_user_id INTEGER NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_ab_practice_pair_team_slot
        UNIQUE (session_id, team_label, slot_number)
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_pairs_id
    ON public.ab_practice_pairs (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_pairs_session_id
    ON public.ab_practice_pairs (session_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_pairs_session_team
    ON public.ab_practice_pairs (session_id, team_label);

CREATE TABLE IF NOT EXISTS public.ab_practice_exposures (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES public.ab_practice_sessions(id),
    student_user_id INTEGER NOT NULL REFERENCES public.users(id),
    pair_id INTEGER NOT NULL REFERENCES public.ab_practice_pairs(id),
    sequence INTEGER NOT NULL,
    image_a_is_left BOOLEAN NOT NULL,
    started_at TIMESTAMPTZ,
    choice VARCHAR(8),
    responded_at TIMESTAMPTZ,
    CONSTRAINT ux_ab_practice_exposure_student_pair
        UNIQUE (session_id, student_user_id, pair_id),
    CONSTRAINT ux_ab_practice_exposure_student_sequence
        UNIQUE (session_id, student_user_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_exposures_id
    ON public.ab_practice_exposures (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_exposures_pair_id
    ON public.ab_practice_exposures (pair_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_exposures_session_id
    ON public.ab_practice_exposures (session_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_exposures_student_user_id
    ON public.ab_practice_exposures (student_user_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_exposures_session_student
    ON public.ab_practice_exposures (session_id, student_user_id);

CREATE TABLE IF NOT EXISTS public.ab_practice_anonymous_participants (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES public.ab_practice_sessions(id),
    serial_number INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_ab_practice_anon_participant_serial
        UNIQUE (session_id, serial_number),
    CONSTRAINT ux_ab_practice_anon_participant_token
        UNIQUE (session_id, token_hash)
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_participants_id
    ON public.ab_practice_anonymous_participants (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_participants_session_id
    ON public.ab_practice_anonymous_participants (session_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anon_participants_session
    ON public.ab_practice_anonymous_participants (session_id);

CREATE TABLE IF NOT EXISTS public.ab_practice_anonymous_exposures (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES public.ab_practice_sessions(id),
    participant_id INTEGER NOT NULL REFERENCES public.ab_practice_anonymous_participants(id),
    pair_id INTEGER NOT NULL REFERENCES public.ab_practice_pairs(id),
    sequence INTEGER NOT NULL,
    image_a_is_left BOOLEAN NOT NULL,
    started_at TIMESTAMPTZ,
    choice VARCHAR(8),
    responded_at TIMESTAMPTZ,
    CONSTRAINT ux_ab_practice_anon_exposure_pair
        UNIQUE (session_id, participant_id, pair_id),
    CONSTRAINT ux_ab_practice_anon_exposure_sequence
        UNIQUE (session_id, participant_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_exposures_id
    ON public.ab_practice_anonymous_exposures (id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_exposures_pair_id
    ON public.ab_practice_anonymous_exposures (pair_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_exposures_participant_id
    ON public.ab_practice_anonymous_exposures (participant_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anonymous_exposures_session_id
    ON public.ab_practice_anonymous_exposures (session_id);
CREATE INDEX IF NOT EXISTS ix_ab_practice_anon_exposures_session_participant
    ON public.ab_practice_anonymous_exposures (session_id, participant_id);

-- A/B 실습 화면 및 API 권한 메타데이터.
-- 기존 (path, method) 행이 있으면 UPDATE하지 않고 건너뜁니다.
WITH ab_route_permissions(path, method, is_public, roles) AS (
    VALUES
        ('/professor/ab-practice', 'GET', FALSE, '["교수"]'::json),
        ('/professor/ab-practice/new', 'GET', FALSE, '["교수"]'::json),
        ('/professor/ab-practice/{session_id}', 'GET', FALSE, '["교수"]'::json),
        ('/professor/ab-practice/{session_id}/edit', 'GET', FALSE, '["교수"]'::json),
        ('/professor/ab-practice/{session_id}/test', 'GET', FALSE, '["교수"]'::json),
        ('/professor/ab-practice/{session_id}/results', 'GET', FALSE, '["교수"]'::json),

        ('/ab-practices/sessions', 'GET', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}', 'GET', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}', 'PATCH', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}', 'DELETE', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/registration:start', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/registration:end', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/test:start', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/vote:end', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/progress', 'GET', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/results', 'GET', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/pairs', 'POST', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/pairs/{pair_id}/{slot}', 'PUT', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/pairs/{pair_id}', 'DELETE', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/pairs/{pair_id}/{slot}', 'DELETE', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/participants/{participant_id}/responses', 'DELETE', FALSE, '["교수"]'::json),
        ('/ab-practices/sessions/{session_id}/students/{student_user_id}/responses', 'DELETE', FALSE, '["교수"]'::json),

        -- QR 업로드는 로그인 필수. 앱에서 허용하는 로그인 역할 목록.
        ('/ab-practices/upload/{token}', 'GET', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),
        ('/ab-practices/upload/{token}/pairs', 'POST', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),
        ('/ab-practices/upload/{token}/pairs/{pair_id}/{slot}', 'PUT', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),
        ('/ab-practices/upload/{token}/pairs/{pair_id}', 'DELETE', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),
        ('/ab-practices/upload/{token}/pairs/{pair_id}/{slot}', 'DELETE', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),
        ('/ab-practice/upload/{token}', 'GET', FALSE, '["user", "가천대학교", "gcs", "token", "교수", "admin"]'::json),

        -- 투표 및 이미지 제공은 QR 세션 토큰을 사용하므로 로그인 불필요.
        ('/ab-practice/test/{token}/participants', 'POST', TRUE, '[]'::json),
        ('/ab-practice/test/{token}', 'GET', TRUE, '[]'::json),
        ('/ab-practice/test/{token}/exposures/{exposure_id}/start', 'POST', TRUE, '[]'::json),
        ('/ab-practice/test/{token}/exposures/{exposure_id}/vote', 'POST', TRUE, '[]'::json),
        ('/ab-practices/assets/{token}/{pair_id}/{slot}', 'GET', TRUE, '[]'::json)
)
INSERT INTO public.route_permissions (path, method, is_public, roles)
SELECT seed.path, seed.method, seed.is_public, seed.roles
FROM ab_route_permissions AS seed
WHERE NOT EXISTS (
    SELECT 1
    FROM public.route_permissions AS existing
    WHERE existing.path = seed.path
      AND existing.method = seed.method
);

COMMIT;
