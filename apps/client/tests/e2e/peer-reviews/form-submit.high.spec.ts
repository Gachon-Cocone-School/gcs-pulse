import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');
const PROFESSOR_EMAIL = 'e2e-peer-form-prof@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Form Professor';

let didEnsureServerSchema = false;

type SessionBootstrapResult = {
  session_cookie: string;
};

type SeedStudentResult = {
  user_id: number;
  user_name: string;
  user_email: string;
  session_cookie: string;
};

type SessionSeedResult = {
  session_id: number;
  form_token: string;
};

function toLocalApiUrl(url: string): string {
  if (url.startsWith(REMOTE_API_ORIGIN)) {
    return url.replace(REMOTE_API_ORIGIN, API_BASE);
  }
  return url;
}

function resolveServerPythonExecutable(): string {
  if (process.env.E2E_SERVER_PYTHON) {
    return process.env.E2E_SERVER_PYTHON;
  }

  const venvPython = resolve(SERVER_ROOT, 'venv/bin/python');
  if (existsSync(venvPython)) {
    return venvPython;
  }

  return 'python3';
}

function runServerPython<T>(script: string, env: Record<string, string>): T {
  const pythonExecutable = resolveServerPythonExecutable();
  const result = spawnSync(pythonExecutable, ['-c', script], {
    cwd: SERVER_ROOT,
    encoding: 'utf-8',
    env: {
      ...process.env,
      PYTHONPATH: SERVER_ROOT,
      ...env,
    },
  });

  if (result.error) {
    throw new Error(`Failed to run server python script: ${result.error.message}`);
  }

  if (result.status !== 0) {
    throw new Error(
      `Server python script failed (exit ${result.status}): ${(result.stderr || result.stdout || '').trim()}`,
    );
  }

  const output = result.stdout
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .at(-1);

  if (!output) {
    throw new Error('Server python script returned empty output');
  }

  return JSON.parse(output) as T;
}

function ensureServerSchemaReady(): void {
  if (didEnsureServerSchema) {
    return;
  }

  const script = [
    'import asyncio',
    'import json',
    'from sqlalchemy import text',
    'from app.database import engine',
    '',
    'async def main() -> None:',
    '    async with engine.begin() as conn:',
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_review_sessions (id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, professor_user_id INTEGER NOT NULL REFERENCES users(id), is_open BOOLEAN NOT NULL DEFAULT TRUE, access_token VARCHAR(128) NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_review_sessions_access_token ON peer_review_sessions(access_token)"))',
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_review_session_members (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES peer_review_sessions(id), student_user_id INTEGER NOT NULL REFERENCES users(id), team_label VARCHAR(64) NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_review_session_member_session_student ON peer_review_session_members(session_id, student_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_review_session_members_session_team ON peer_review_session_members(session_id, team_label)"))',
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_review_submissions (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES peer_review_sessions(id), evaluator_user_id INTEGER NOT NULL REFERENCES users(id), evaluatee_user_id INTEGER NOT NULL REFERENCES users(id), contribution_percent INTEGER NOT NULL, fit_yes_no BOOLEAN NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_review_submission_session_evaluator_evaluatee ON peer_review_submissions(session_id, evaluator_user_id, evaluatee_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_review_submission_session_evaluator ON peer_review_submissions(session_id, evaluator_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_review_submission_session_evaluatee ON peer_review_submissions(session_id, evaluatee_user_id)"))',
    '    print(json.dumps({"ok": True}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  runServerPython<{ ok: true }>(script, {});
  didEnsureServerSchema = true;
}

function bootstrapSignedSessionCookie(email: string, name: string, roles: string[]): string {
  const script = [
    'import asyncio',
    'import base64',
    'import json',
    'import os',
    'from sqlalchemy import select',
    'from itsdangerous import TimestampSigner',
    'from app import crud',
    'from app.core.config import settings',
    'from app.database import AsyncSessionLocal',
    'from app.models import User',
    '',
    'EMAIL = os.environ["E2E_SESSION_EMAIL"]',
    'NAME = os.environ["E2E_SESSION_NAME"]',
    'ROLES = [role.strip() for role in os.environ.get("E2E_SESSION_ROLES", "가천대학교").split(",") if role.strip()]',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": EMAIL,',
    '                "name": NAME,',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '        user_result = await db.execute(select(User).filter(User.email == EMAIL))',
    '        user = user_result.scalars().first()',
    '        if not user:',
    '            raise RuntimeError("Failed to resolve user")',
    '        user.roles = ROLES or ["가천대학교"]',
    '        await db.commit()',
    '',
    '    payload = {',
    '        "user": {',
    '            "email": EMAIL,',
    '            "name": NAME,',
    '            "picture": "",',
    '            "email_verified": True,',
    '        }',
    '    }',
    '    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))',
    '    cookie = TimestampSigner(str(settings.SECRET_KEY)).sign(encoded).decode("utf-8")',
    '    print(json.dumps({"session_cookie": cookie}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  const result = runServerPython<SessionBootstrapResult>(script, {
    E2E_SESSION_EMAIL: email,
    E2E_SESSION_NAME: name,
    E2E_SESSION_ROLES: roles.join(','),
  });

  if (!result.session_cookie) {
    throw new Error('Signed session bootstrap did not return session_cookie');
  }

  return result.session_cookie;
}

function seedStudent(email: string, name: string): SeedStudentResult {
  const script = [
    'import asyncio',
    'import base64',
    'import json',
    'import os',
    'from sqlalchemy import select',
    'from itsdangerous import TimestampSigner',
    'from app import crud',
    'from app.core.config import settings',
    'from app.database import AsyncSessionLocal',
    'from app.models import User',
    '',
    'EMAIL = os.environ["E2E_STUDENT_EMAIL"]',
    'NAME = os.environ["E2E_STUDENT_NAME"]',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": EMAIL,',
    '                "name": NAME,',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '        user_result = await db.execute(select(User).filter(User.email == EMAIL))',
    '        user = user_result.scalars().first()',
    '        if not user:',
    '            raise RuntimeError("Failed to resolve student user")',
    '        user.roles = ["가천대학교"]',
    '        await db.commit()',
    '',
    '    payload = {',
    '        "user": {',
    '            "email": EMAIL,',
    '            "name": NAME,',
    '            "picture": "",',
    '            "email_verified": True,',
    '        }',
    '    }',
    '    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))',
    '    cookie = TimestampSigner(str(settings.SECRET_KEY)).sign(encoded).decode("utf-8")',
    '    print(json.dumps({"user_id": user.id, "user_name": user.name, "user_email": user.email, "session_cookie": cookie}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  return runServerPython<SeedStudentResult>(script, {
    E2E_STUDENT_EMAIL: email,
    E2E_STUDENT_NAME: name,
  });
}

function seedSessionWithMembers(professorEmail: string, studentA: SeedStudentResult, studentB: SeedStudentResult): SessionSeedResult {
  const script = [
    'import asyncio',
    'import json',
    'import os',
    'import secrets',
    'from sqlalchemy import select',
    'from app.database import AsyncSessionLocal',
    'from app.models import User',
    'from app import crud_peer_reviews as peer_review_crud',
    '',
    'PROFESSOR_EMAIL = os.environ["E2E_PROF_EMAIL"]',
    'STUDENT_A_ID = int(os.environ["E2E_STUDENT_A_ID"] or "0")',
    'STUDENT_B_ID = int(os.environ["E2E_STUDENT_B_ID"] or "0")',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        prof_result = await db.execute(select(User).filter(User.email == PROFESSOR_EMAIL))',
    '        professor = prof_result.scalars().first()',
    '        if not professor:',
    '            raise RuntimeError("Professor not found")',
    '',
    '        session = await peer_review_crud.create_session(',
    '            db,',
    '            title="E2E 학생 폼 세션",',
    '            professor_user_id=professor.id,',
    '            access_token="e2e-form-token-" + secrets.token_urlsafe(8),',
    '        )',
    '',
    '        await peer_review_crud.replace_session_members(',
    '            db,',
    '            session_id=session.id,',
    '            members=[(STUDENT_A_ID, "1조"), (STUDENT_B_ID, "1조")],',
    '        )',
    '',
    '        print(json.dumps({"session_id": session.id, "form_token": session.access_token}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  return runServerPython<SessionSeedResult>(script, {
    E2E_PROF_EMAIL: professorEmail,
    E2E_STUDENT_A_ID: String(studentA.user_id),
    E2E_STUDENT_B_ID: String(studentB.user_id),
  });
}

async function setSessionCookieForApi(page: Page, sessionCookie: string): Promise<void> {
  const apiUrl = new URL(API_BASE);
  const host = apiUrl.hostname === 'localhost' ? '127.0.0.1' : apiUrl.hostname;

  await page.context().addCookies([
    {
      name: 'session',
      value: sessionCookie,
      domain: host,
      path: '/',
      httpOnly: true,
      secure: apiUrl.protocol === 'https:',
      sameSite: 'Lax',
      expires: Math.floor(Date.now() / 1000) + 14 * 24 * 60 * 60,
    },
  ]);
}

async function setupApiProxy(page: Page): Promise<void> {
  await Promise.all(
    API_PROXY_ORIGINS.map((origin) =>
      page.route(`${origin}/**`, async (route) => {
        const request = route.request();
        const targetUrl = toLocalApiUrl(request.url());

        if (targetUrl.includes('/notification/public/sse')) {
          await route.fulfill({
            status: 204,
            contentType: 'text/plain; charset=utf-8',
            body: '',
          });
          return;
        }

        const headers = {
          ...request.headers(),
        };
        delete headers.host;

        const cookies = await page.context().cookies(API_BASE);
        if (cookies.length > 0) {
          headers.cookie = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
        }

        const response = await page.request.fetch(targetUrl, {
          method: request.method(),
          headers,
          data: request.postDataBuffer() ?? undefined,
          failOnStatusCode: false,
        });

        await route.fulfill({
          status: response.status(),
          headers: response.headers(),
          body: await response.body(),
        });
      }),
    ),
  );
}

test.describe('Peer feedback form submit High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(() => {
    ensureServerSchemaReady();
  });

  test('[CHK-PEER-FORM-001] @high 학생 폼 진입 및 팀원 렌더링', async ({ page }) => {
    const professorCookie = bootstrapSignedSessionCookie(PROFESSOR_EMAIL, PROFESSOR_NAME, ['교수']);
    expect(professorCookie).toBeTruthy();

    const studentA = seedStudent('e2e-form-student-a@gachon.ac.kr', '폼 학생 A');
    const studentB = seedStudent('e2e-form-student-b@gachon.ac.kr', '폼 학생 B');
    const seededSession = seedSessionWithMembers(PROFESSOR_EMAIL, studentA, studentB);

    await setSessionCookieForApi(page, studentA.session_cookie);
    await setupApiProxy(page);

    try {
      await page.goto(`/peer-reviews/forms/${seededSession.form_token}`);
      await expect(page).toHaveURL(new RegExp(`/peer-reviews/forms/${seededSession.form_token}`));

      const main = page.getByRole('main');
      await expect(main.getByRole('heading', { name: '동료 피드백 폼' })).toBeVisible();
      await expect(main.getByText(studentA.user_name)).toBeVisible();
      await expect(main.getByText(studentB.user_name)).toBeVisible();
      await expect(main.getByText(/현재 합계:/)).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('[CHK-PEER-FORM-002] @high Slider 조작 시 합계 100 유지 및 위 항목 고정', async ({ page }) => {
    const studentA = seedStudent('e2e-form-student-c@gachon.ac.kr', '폼 학생 C');
    const studentB = seedStudent('e2e-form-student-d@gachon.ac.kr', '폼 학생 D');
    const seededSession = seedSessionWithMembers(PROFESSOR_EMAIL, studentA, studentB);

    await setSessionCookieForApi(page, studentA.session_cookie);
    await setupApiProxy(page);

    try {
      await page.goto(`/peer-reviews/forms/${seededSession.form_token}`);
      await expect(page).toHaveURL(new RegExp(`/peer-reviews/forms/${seededSession.form_token}`));

      const sliders = page.locator('[data-testid^="contribution-slider-"]');
      await expect(sliders).toHaveCount(2);

      const firstUserId = (await sliders.nth(0).getAttribute('data-testid'))?.replace('contribution-slider-', '');
      const secondUserId = (await sliders.nth(1).getAttribute('data-testid'))?.replace('contribution-slider-', '');
      expect(firstUserId).toBeTruthy();
      expect(secondUserId).toBeTruthy();

      await sliders.nth(0).fill('80');
      await expect(page.getByText('현재 합계: 100 / 100')).toBeVisible();
      await expect(page.getByTestId(`contribution-value-${firstUserId}`)).toHaveText('80%');
      await expect(page.getByTestId(`contribution-value-${secondUserId}`)).toHaveText('20%');

      await expect(sliders.nth(1)).toBeDisabled();
      await expect(page.getByText('현재 합계: 100 / 100')).toBeVisible();
      await expect(page.getByTestId(`contribution-value-${firstUserId}`)).toHaveText('80%');
      await expect(page.getByTestId(`contribution-value-${secondUserId}`)).toHaveText('20%');
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('[CHK-PEER-FORM-003] @high 정상 제출 후 상태/요약 반영', async ({ page }) => {
    const studentA = seedStudent('e2e-form-student-e@gachon.ac.kr', '폼 학생 E');
    const studentB = seedStudent('e2e-form-student-f@gachon.ac.kr', '폼 학생 F');
    const seededSession = seedSessionWithMembers(PROFESSOR_EMAIL, studentA, studentB);

    await setSessionCookieForApi(page, studentA.session_cookie);
    await setupApiProxy(page);

    try {
      await page.goto(`/peer-reviews/forms/${seededSession.form_token}`);
      await expect(page).toHaveURL(new RegExp(`/peer-reviews/forms/${seededSession.form_token}`));

      const sliders = page.locator('[data-testid^="contribution-slider-"]');
      await expect(sliders).toHaveCount(2);
      await sliders.nth(0).fill('70');

      await expect(page.getByRole('heading', { name: '팀 제출 현황' })).toHaveCount(0);

      const submitResPromise = page.waitForResponse(
        (res) => res.url().includes(`/peer-reviews/forms/${seededSession.form_token}/submit`) && res.request().method() === 'POST',
      );

      await page.getByRole('button', { name: '제출' }).click();

      const submitRes = await submitResPromise;
      expect(submitRes.ok()).toBeTruthy();

      const main = page.getByRole('main');
      await expect(main.getByText('제출이 완료되었습니다.')).toBeVisible();
      await expect(main.getByText('제출완료')).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('[CHK-PEER-FORM-004] @high SSE 수신 시 종료 상태 즉시 반영', async ({ page }) => {
    const studentA = seedStudent('e2e-form-student-g@gachon.ac.kr', '폼 학생 G');
    const studentB = seedStudent('e2e-form-student-h@gachon.ac.kr', '폼 학생 H');
    const seededSession = seedSessionWithMembers(PROFESSOR_EMAIL, studentA, studentB);

    await setSessionCookieForApi(page, studentA.session_cookie);
    await setupApiProxy(page);

    await page.route('**/notification/public/sse', async (route) => {
      await route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
          'cache-control': 'no-cache',
          connection: 'keep-alive',
        },
        body: `event: peer_review_session_status\ndata: {"session_id": ${seededSession.session_id}, "is_open": false, "updated_at": "2026-03-11T00:00:00+09:00"}\n\n`,
      });
    });

    try {
      await page.goto(`/peer-reviews/forms/${seededSession.form_token}`);
      await expect(page).toHaveURL(new RegExp(`/peer-reviews/forms/${seededSession.form_token}`));

      await expect(page.getByRole('button', { name: '제출' })).toBeDisabled();
      await expect(page.locator('span').filter({ hasText: /^종료$/ })).toBeVisible();
      await expect(page.getByText('세션이 종료되어 제출할 수 없습니다.')).toBeVisible();
    } finally {
      await page.unroute('**/notification/public/sse');
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('[CHK-PEER-FORM-005] @high 세션 미소속 학생 접근 거부', async ({ request }) => {
    const studentA = seedStudent('e2e-form-student-i@gachon.ac.kr', '폼 학생 I');
    const studentB = seedStudent('e2e-form-student-j@gachon.ac.kr', '폼 학생 J');
    const outsider = seedStudent('e2e-form-student-out@gachon.ac.kr', '폼 외부 학생');
    const seededSession = seedSessionWithMembers(PROFESSOR_EMAIL, studentA, studentB);

    const res = await request.get(`${API_BASE}/peer-reviews/forms/${seededSession.form_token}`, {
      headers: {
        cookie: `session=${outsider.session_cookie}`,
      },
    });

    expect(res.status()).toBe(403);
  });
});
