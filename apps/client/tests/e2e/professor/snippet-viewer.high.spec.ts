import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');

const PROFESSOR_EMAIL = 'e2e-professor-snippet@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Snippet Professor';
const STUDENT_DUP_NAME = 'E2E동명이인학생';
const STUDENT_A_EMAIL = 'e2e-snippet-dup-a@gachon.ac.kr';
const STUDENT_B_EMAIL = 'e2e-snippet-dup-b@gachon.ac.kr';

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

function ensureProfessorSnippetFixtures() {
  const script = [
    'import asyncio',
    'import json',
    'import os',
    'from datetime import date',
    'from sqlalchemy import select, delete',
    'from app.database import AsyncSessionLocal',
    'from app import crud',
    'from app.models import User, Term, Consent, DailySnippet, WeeklySnippet',
    '',
    'PROF_EMAIL = os.environ["E2E_PROF_EMAIL"]',
    'PROF_NAME = os.environ["E2E_PROF_NAME"]',
    'STUDENT_NAME = os.environ["E2E_STUDENT_DUP_NAME"]',
    'STUDENT_A_EMAIL = os.environ["E2E_STUDENT_A_EMAIL"]',
    'STUDENT_B_EMAIL = os.environ["E2E_STUDENT_B_EMAIL"]',
    '',
    'async def upsert_user(db, email: str, name: str, ensure_professor: bool = False):',
    '    await crud.create_or_update_user(',
    '        db,',
    '        {',
    '            "email": email,',
    '            "name": name,',
    '            "picture": "",',
    '            "email_verified": True,',
    '        },',
    '    )',
    '    result = await db.execute(select(User).filter(User.email == email))',
    '    user = result.scalars().first()',
    '    if user is None:',
    '        raise RuntimeError(f"Failed to resolve user: {email}")',
    '    roles = user.roles if isinstance(user.roles, list) else []',
    '    normalized = [str(role).strip() for role in roles if str(role).strip()]',
    '    if ensure_professor:',
    '        if "교수" not in normalized:',
    '            normalized.append("교수")',
    '    else:',
    '        normalized = [role for role in normalized if role not in {"교수", "admin"}]',
    '        if "gcs" not in normalized:',
    '            normalized.append("gcs")',
    '    user.roles = normalized',
    '    return user',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        professor = await upsert_user(db, PROF_EMAIL, PROF_NAME, ensure_professor=True)',
    '        student_a = await upsert_user(db, STUDENT_A_EMAIL, STUDENT_NAME)',
    '        student_b = await upsert_user(db, STUDENT_B_EMAIL, STUDENT_NAME)',
    '',
    '        required_terms_result = await db.execute(select(Term).filter(Term.is_active == True, Term.is_required == True))',
    '        required_terms = list(required_terms_result.scalars().all())',
    '        if required_terms:',
    '            await db.execute(delete(Consent).where(Consent.user_id == professor.id))',
    '            db.add_all([Consent(user_id=professor.id, term_id=term.id) for term in required_terms])',
    '',
    '        await db.execute(delete(DailySnippet).where(DailySnippet.user_id.in_([student_a.id, student_b.id])))',
    '        await db.execute(delete(WeeklySnippet).where(WeeklySnippet.user_id.in_([student_a.id, student_b.id])))',
    '',
    '        db.add_all([',
    '            DailySnippet(user_id=student_a.id, date=date(2026, 3, 10), content="A daily 2026-03-10"),',
    '            DailySnippet(user_id=student_a.id, date=date(2026, 3, 11), content="A daily 2026-03-11"),',
    '            DailySnippet(user_id=student_b.id, date=date(2026, 3, 11), content="B daily 2026-03-11"),',
    '            WeeklySnippet(user_id=student_a.id, week=date(2026, 3, 9), content="A weekly 2026-03-09"),',
    '            WeeklySnippet(user_id=student_a.id, week=date(2026, 3, 2), content="A weekly 2026-03-02"),',
    '            WeeklySnippet(user_id=student_b.id, week=date(2026, 3, 9), content="B weekly 2026-03-09"),',
    '        ])',
    '        await db.commit()',
    '        print(json.dumps({"ok": True, "professor_id": professor.id, "student_a_id": student_a.id, "student_b_id": student_b.id}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  return runServerPython<{ ok: true; professor_id: number; student_a_id: number; student_b_id: number }>(script, {
    E2E_PROF_EMAIL: PROFESSOR_EMAIL,
    E2E_PROF_NAME: PROFESSOR_NAME,
    E2E_STUDENT_DUP_NAME: STUDENT_DUP_NAME,
    E2E_STUDENT_A_EMAIL: STUDENT_A_EMAIL,
    E2E_STUDENT_B_EMAIL: STUDENT_B_EMAIL,
  });
}

async function setSessionCookieForApi(page: Page, sessionCookie: string): Promise<void> {
  const apiUrl = new URL(API_BASE);
  const hosts = apiUrl.hostname === 'localhost' ? ['localhost', '127.0.0.1'] : [apiUrl.hostname];

  await page.context().addCookies(
    hosts.map((host) => ({
      name: 'session',
      value: sessionCookie,
      domain: host,
      path: '/',
      httpOnly: true,
      secure: apiUrl.protocol === 'https:',
      sameSite: 'Lax' as const,
      expires: Math.floor(Date.now() / 1000) + 14 * 24 * 60 * 60,
    })),
  );
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

        const requestUrl = new URL(request.url());
        const testNow = requestUrl.searchParams.get('test_now');
        if (testNow) {
          headers['x-test-now'] = testNow;
        }

        const cookies = await page.context().cookies(API_BASE);
        if (cookies.length > 0) {
          headers.cookie = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
        }

        const response = await route.fetch({
          url: targetUrl,
          headers,
        });

        await route.fulfill({ response });
      }),
    ),
  );
}

test.describe('Professor snippet viewer High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  let studentAId = 0;

  test.beforeAll(() => {
    const fixtures = ensureProfessorSnippetFixtures();
    studentAId = fixtures.student_a_id;
  });

  test.beforeEach(async ({ page }) => {
    await setSessionCookieForApi(page, ensureProfessorSessionCookie());
    await setupApiProxy(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-PROF-SNIP-001] @high 학생 선택 전 스니펫 영역 비노출', async ({ page }) => {
    await page.goto('/professor');
    await expect(page).toHaveURL(/\/professor/);

    await expect(page.getByText('학생 선택')).toBeVisible();
    await expect(page.getByRole('heading', { name: /일간 :|주간 :/ })).toHaveCount(0);
    await expect(page.getByText('저장하기')).toHaveCount(0);
  });

  test('[CHK-PROF-SNIP-002] @high 동명이인 검색 시 정확히 한 명 선택 후 노출', async ({ page }) => {
    await page.goto('/professor');

    await page.getByLabel('학생 검색').fill(STUDENT_DUP_NAME);
    const candidates = page.locator('[data-testid="professor-student-candidates"] label');
    await expect(candidates).toHaveCount(2);

    await expect(page.getByText('저장하기')).toHaveCount(0);

    await page.goto(`/professor?q=${encodeURIComponent(STUDENT_DUP_NAME)}&student_user_id=${studentAId}`);

    await expect(page.getByRole('heading', { name: /^일간\s*:/ })).toBeVisible();
    await expect(page.getByText('저장하기')).toHaveCount(0);
  });

  test('[CHK-PROF-SNIP-003] @high 일간 날짜 이동/좌우 이동 동작', async ({ page }) => {
    await page.goto(
      `/professor?kind=daily&q=${encodeURIComponent(STUDENT_DUP_NAME)}&student_user_id=${studentAId}&date=2026-03-11&test_now=2026-03-11T12:00:00`,
    );

    const dateInput = page.getByLabel('일간 조회 날짜 선택');
    await expect(dateInput).toHaveValue('2026-03-11');
    await expect(page.getByText('A daily 2026-03-11')).toBeVisible();

    await expect(page.getByTitle('이전 스니펫')).toBeEnabled();
    await page.getByTitle('이전 스니펫').click();
    await expect(page).toHaveURL(/id=/);
    await expect(page.getByText('A daily 2026-03-10')).toBeVisible();

    await expect(page.getByTitle('다음 스니펫')).toBeEnabled();
    await page.getByTitle('다음 스니펫').click();
    await expect(page.getByText('A daily 2026-03-11')).toBeVisible();
  });

  test('[CHK-PROF-SNIP-004] @high 입력 재변경 시 선택 무효화', async ({ page }) => {
    await page.goto(`/professor?q=${encodeURIComponent(STUDENT_DUP_NAME)}&student_user_id=${studentAId}`);
    await expect(page.getByRole('heading', { name: /^일간\s*:/ })).toBeVisible();

    await page.getByLabel('학생 검색').fill('존재하지않는학생');

    await expect(page.getByRole('heading', { name: /^일간\s*:/ })).toHaveCount(0);
    await expect(page).not.toHaveURL(/student_user_id=/);
  });

  test('[CHK-PROF-SNIP-005] @high 주간 전환 후 날짜/이동 동작', async ({ page }) => {
    await page.goto(
      `/professor?kind=weekly&q=${encodeURIComponent(STUDENT_DUP_NAME)}&student_user_id=${studentAId}&week=2026-03-09&test_now=2026-03-11T12:00:00`,
    );

    const weekInput = page.getByLabel('주간 조회 날짜 선택');
    await expect(weekInput).toHaveValue('2026-03-09');

    await expect(page.getByText('A weekly 2026-03-09')).toBeVisible();

    await expect(page.getByTitle('이전 주')).toBeEnabled();
    await page.getByTitle('이전 주').click();
    await expect(page).toHaveURL(/id=/);
    await expect(page.getByText('A weekly 2026-03-02')).toBeVisible();

    await expect(page.getByTitle('다음 주')).toBeEnabled();
    await page.getByTitle('다음 주').click();
    await expect(page.getByText('A weekly 2026-03-09')).toBeVisible();
  });
});
