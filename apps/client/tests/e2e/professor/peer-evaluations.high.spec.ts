import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');
const PROFESSOR_EMAIL = 'e2e-professor-peer@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Peer Professor';
const STUDENT_ALPHA_EMAIL = 'e2e-peer-student-alpha@gachon.ac.kr';
const STUDENT_ALPHA_NAME = 'E2EPeerStudentAlpha';
const STUDENT_BETA_EMAIL = 'e2e-peer-student-beta@gachon.ac.kr';
const STUDENT_BETA_NAME = 'E2EPeerStudentBeta';

let didEnsureServerSchema = false;
let cachedProfessorSessionCookie: string | null = null;

type SessionBootstrapResult = {
  session_cookie: string;
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
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_evaluation_sessions (id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, professor_user_id INTEGER NOT NULL REFERENCES users(id), is_open BOOLEAN NOT NULL DEFAULT TRUE, access_token VARCHAR(128) NOT NULL, raw_text TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("ALTER TABLE peer_evaluation_sessions ADD COLUMN IF NOT EXISTS raw_text TEXT"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_evaluation_sessions_access_token ON peer_evaluation_sessions(access_token)"))',
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_evaluation_session_members (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES peer_evaluation_sessions(id), student_user_id INTEGER NOT NULL REFERENCES users(id), team_label VARCHAR(64) NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_eval_session_member_session_student ON peer_evaluation_session_members(session_id, student_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_eval_session_members_session_team ON peer_evaluation_session_members(session_id, team_label)"))',
    '        await conn.execute(text("CREATE TABLE IF NOT EXISTS peer_evaluation_submissions (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES peer_evaluation_sessions(id), evaluator_user_id INTEGER NOT NULL REFERENCES users(id), evaluatee_user_id INTEGER NOT NULL REFERENCES users(id), contribution_percent INTEGER NOT NULL, fit_yes_no BOOLEAN NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))',
    '        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_peer_eval_submission_session_evaluator_evaluatee ON peer_evaluation_submissions(session_id, evaluator_user_id, evaluatee_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_eval_submission_session_evaluator ON peer_evaluation_submissions(session_id, evaluator_user_id)"))',
    '        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_peer_eval_submission_session_evaluatee ON peer_evaluation_submissions(session_id, evaluatee_user_id)"))',
    '    print(json.dumps({"ok": True}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  runServerPython<{ ok: true }>(script, {});
  didEnsureServerSchema = true;
}

function ensureStudentFixtures(): void {
  const script = [
    'import asyncio',
    'import json',
    'import os',
    'from app import crud',
    'from app.database import AsyncSessionLocal',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": os.environ["E2E_STUDENT_ALPHA_EMAIL"],',
    '                "name": os.environ["E2E_STUDENT_ALPHA_NAME"],',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": os.environ["E2E_STUDENT_BETA_EMAIL"],',
    '                "name": os.environ["E2E_STUDENT_BETA_NAME"],',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '    print(json.dumps({"ok": True}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  runServerPython<{ ok: true }>(script, {
    E2E_STUDENT_ALPHA_EMAIL: STUDENT_ALPHA_EMAIL,
    E2E_STUDENT_ALPHA_NAME: STUDENT_ALPHA_NAME,
    E2E_STUDENT_BETA_EMAIL: STUDENT_BETA_EMAIL,
    E2E_STUDENT_BETA_NAME: STUDENT_BETA_NAME,
  });
}

function bootstrapProfessorSessionCookie(email: string, name: string): string {
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
    '            raise RuntimeError("Failed to resolve professor user")',
    '        roles = user.roles if isinstance(user.roles, list) else []',
    '        normalized = [str(role).strip() for role in roles if str(role).strip()]',
    '        if "교수" not in normalized:',
    '            normalized.append("교수")',
    '        user.roles = normalized',
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
  });

  if (!result.session_cookie) {
    throw new Error('Professor signed session bootstrap did not return session_cookie');
  }

  return result.session_cookie;
}

function ensureProfessorSessionCookie(): string {
  if (cachedProfessorSessionCookie) {
    return cachedProfessorSessionCookie;
  }

  cachedProfessorSessionCookie = bootstrapProfessorSessionCookie(PROFESSOR_EMAIL, PROFESSOR_NAME);
  return cachedProfessorSessionCookie;
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

function uniqueTitle(prefix: string): string {
  return `${prefix}-${Date.now()}`;
}

test.describe('Professor peer feedback High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(() => {
    ensureServerSchemaReady();
    ensureStudentFixtures();
  });

  test.beforeEach(async ({ page }) => {
    await setSessionCookieForApi(page, ensureProfessorSessionCookie());
    await setupApiProxy(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-PEER-PROF-001] @high 메인 화면은 리스트 중심 UI만 노출', async ({ page }) => {
    await page.goto('/professor/peer-reviews');
    await expect(page).toHaveURL(/\/professor\/peer-reviews/);

    await expect(page.getByRole('button', { name: '생성하기' })).toBeVisible();
    await expect(page.getByText('내 세션 목록')).toBeVisible();

    await expect(page.getByText('팀 구성 입력/확정')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '취소' })).toHaveCount(0);
  });

  test('[CHK-PEER-PROF-002] @high 생성 직후 편집 페이지로 자동 이동', async ({ page }) => {
    await page.goto('/professor/peer-reviews');

    const createResPromise = page.waitForResponse(
      (res) =>
        res.url().includes('/peer-reviews/sessions') &&
        res.request().method() === 'POST' &&
        !res.url().includes('members:parse'),
    );

    await page.getByRole('button', { name: '생성하기' }).click();
    const createRes = await createResPromise;
    expect(createRes.ok()).toBeTruthy();

    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);
    await expect(page.getByTestId('peer-eval-edit-title-input')).toHaveValue('새 동료 피드백 세션');
  });

  test('[CHK-PEER-PROF-003] @high 메인에서 편집 클릭 시 edit 페이지 이동', async ({ page }) => {
    await page.goto('/professor/peer-reviews');
    await page.getByRole('button', { name: '생성하기' }).click();
    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);

    await page.getByRole('button', { name: '취소' }).click();
    await expect(page).toHaveURL('/professor/peer-reviews');

    const row = page.locator('tr', { hasText: '새 동료 피드백 세션' }).first();
    await row.getByRole('link', { name: '편집' }).click();

    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);
  });
  test('[CHK-PEER-PROF-004] @high 편집 페이지에서 저장 반영', async ({ page }) => {
    const updatedTitle = uniqueTitle('E2E 제목수정후');

    await page.goto('/professor/peer-reviews');
    await page.getByRole('button', { name: '생성하기' }).click();
    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);

    await page.getByTestId('peer-eval-edit-title-input').fill(updatedTitle);
    await page.getByTestId('peer-eval-edit-raw-input').fill(
      `1조: ${STUDENT_ALPHA_NAME}, ${STUDENT_BETA_NAME}`,
    );

    const parseResPromise = page.waitForResponse(
      (res) => res.url().includes('/members:parse') && res.request().method() === 'POST',
    );
    await page.getByTestId('peer-eval-edit-parse-button').click();
    const parseRes = await parseResPromise;
    expect(parseRes.ok()).toBeTruthy();

    const patchResPromise = page.waitForResponse(
      (res) => /\/peer-reviews\/sessions\/\d+$/.test(res.url()) && res.request().method() === 'PATCH',
    );

    await page.getByTestId('peer-eval-edit-save-all').click();
    const patchRes = await patchResPromise;
    expect(patchRes.ok()).toBeTruthy();

    await page.getByRole('button', { name: '취소' }).click();
    await expect(page).toHaveURL('/professor/peer-reviews');

    const updatedRow = page.locator('tr', { hasText: updatedTitle }).first();
    await expect(updatedRow).toBeVisible();

    const updatedAtCell = updatedRow.locator('td').nth(2);
    await expect(updatedAtCell).not.toHaveText('-');
    await expect(updatedAtCell).not.toHaveText('');
  });

  test('[CHK-PEER-PROF-005] @high 경고 해소 후 canonical 원문 저장 및 재진입 preload', async ({ page }) => {
    const updatedTitle = uniqueTitle('E2E 구성저장');

    await page.goto('/professor/peer-reviews');
    await page.getByRole('button', { name: '생성하기' }).click();
    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);

    await page.getByTestId('peer-eval-edit-title-input').fill(updatedTitle);
    await page.getByTestId('peer-eval-edit-raw-input').fill(`1조: ${STUDENT_ALPHA_NAME}, UnknownStudent`);

    const parseWarnResPromise = page.waitForResponse(
      (res) => res.url().includes('/members:parse') && res.request().method() === 'POST',
    );
    await page.getByTestId('peer-eval-edit-parse-button').click();
    const parseWarnRes = await parseWarnResPromise;
    expect(parseWarnRes.ok()).toBeTruthy();

    await expect(page.getByTestId('peer-eval-edit-unresolved-list')).toBeVisible();
    await expect(page.getByTestId('peer-eval-edit-save-all')).toBeDisabled();

    await page.getByTestId('peer-eval-edit-raw-input').fill(`1조: ${STUDENT_ALPHA_NAME}, ${STUDENT_BETA_NAME}`);

    const parseCleanResPromise = page.waitForResponse(
      (res) => res.url().includes('/members:parse') && res.request().method() === 'POST',
    );
    await page.getByTestId('peer-eval-edit-parse-button').click();
    const parseCleanRes = await parseCleanResPromise;
    expect(parseCleanRes.ok()).toBeTruthy();

    await expect(page.getByTestId('peer-eval-edit-parse-clean')).toBeVisible();
    await expect(page.getByTestId('peer-eval-edit-save-all')).toBeEnabled();
    await expect(page.getByTestId('peer-eval-edit-raw-input')).toHaveValue(
      `1조: ${STUDENT_ALPHA_NAME}, ${STUDENT_BETA_NAME}`,
    );

    const patchResPromise = page.waitForResponse(
      (res) => /\/peer-reviews\/sessions\/\d+$/.test(res.url()) && res.request().method() === 'PATCH',
    );
    const confirmResPromise = page.waitForResponse(
      (res) => res.url().includes('/members:confirm') && res.request().method() === 'POST',
    );

    await page.getByTestId('peer-eval-edit-save-all').click();
    const patchRes = await patchResPromise;
    const confirmRes = await confirmResPromise;
    expect(patchRes.ok()).toBeTruthy();
    expect(confirmRes.ok()).toBeTruthy();

    await page.getByRole('button', { name: '취소' }).click();
    await expect(page).toHaveURL('/professor/peer-reviews');

    const updatedRow = page.locator('tr', { hasText: updatedTitle }).first();
    await expect(updatedRow).toBeVisible();
    await updatedRow.getByRole('link', { name: '편집' }).click();

    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);
    await expect(page.getByTestId('peer-eval-edit-raw-input')).toHaveValue(
      `1조: ${STUDENT_ALPHA_NAME}, ${STUDENT_BETA_NAME}`,
    );
  });

  test('[CHK-PEER-PROF-006] @high parse 진행 중 취소 버튼으로 요청 중단', async ({ page }) => {
    await page.goto('/professor/peer-reviews');
    await page.getByRole('button', { name: '생성하기' }).click();
    await expect(page).toHaveURL(/\/professor\/peer-reviews\/\d+\/edit/);

    await page.getByTestId('peer-eval-edit-raw-input').fill(`1조: ${STUDENT_ALPHA_NAME}, ${STUDENT_BETA_NAME}`);

    await page.route('**/peer-reviews/sessions/*/members:parse', async (route) => {
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          teams: {
            '1조': [
              {
                team_label: '1조',
                raw_name: STUDENT_ALPHA_NAME,
                student_user_id: 1,
                student_name: STUDENT_ALPHA_NAME,
                student_email: STUDENT_ALPHA_EMAIL,
              },
            ],
          },
          unresolved_members: [],
        }),
      });
    });

    await page.getByTestId('peer-eval-edit-parse-button').click();
    await expect(page.getByTestId('peer-eval-edit-parse-cancel')).toBeVisible();

    await page.getByTestId('peer-eval-edit-parse-cancel').click();
    await expect(page.getByText('팀 구성 불러오기가 취소되었습니다.')).toBeVisible();
    await expect(page.getByTestId('peer-eval-edit-parse-cancel')).toHaveCount(0);

    await page.unroute('**/peer-reviews/sessions/*/members:parse');
  });
});
