import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://127.0.0.1:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'https://api-dev.1000.school';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');
const PROFESSOR_EMAIL = 'e2e-professor@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Professor';

let didEnsureServerMigration = false;
let cachedProfessorSessionCookie: string | null = null;

type SeedProfessorStudentResult = {
  user_id: number;
  user_name: string;
  user_email: string;
  daily_snippet_id: number;
  weekly_snippet_id: number;
};

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
  if (didEnsureServerMigration) {
    return;
  }

  const script = [
    'import asyncio',
    'import json',
    'from sqlalchemy import inspect, text',
    'from app.database import engine',
    'from app.models import Comment, StudentRiskSnapshot',
    '',
    'def _ensure_comment_type_column(sync_conn) -> bool:',
    '    inspector = inspect(sync_conn)',
    '    if "comments" not in inspector.get_table_names():',
    '        Comment.__table__.create(sync_conn, checkfirst=True)',
    '        inspector = inspect(sync_conn)',
    '    columns = inspector.get_columns("comments")',
    '    return any(col.get("name") == "comment_type" for col in columns)',
    '',
    'def _ensure_model_indexes(sync_conn, model) -> None:',
    '    for index in model.__table__.indexes:',
    '        index.create(sync_conn, checkfirst=True)',
    '',
    'async def main() -> None:',
    '    async with engine.begin() as conn:',
    '        comment_type_exists = await conn.run_sync(_ensure_comment_type_column)',
    '        if not comment_type_exists:',
    '            await conn.execute(',
    '                text("ALTER TABLE comments ADD COLUMN comment_type VARCHAR(16) NOT NULL DEFAULT \'peer\'")',
    '            )',
    '        await conn.execute(',
    '            text("UPDATE comments SET comment_type = \'peer\' WHERE comment_type IS NULL OR comment_type = \'\'")',
    '        )',
    '',
    '        await conn.run_sync(lambda sync_conn: StudentRiskSnapshot.__table__.create(sync_conn, checkfirst=True))',
    '        await conn.run_sync(lambda sync_conn: _ensure_model_indexes(sync_conn, Comment))',
    '        await conn.run_sync(lambda sync_conn: _ensure_model_indexes(sync_conn, StudentRiskSnapshot))',
    '',
    '    print(json.dumps({"ok": True}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  runServerPython<{ ok: true }>(script, {});
  didEnsureServerMigration = true;
}

function seedProfessorStudentFixture(): SeedProfessorStudentResult {
  const script = [
    'import asyncio',
    'import json',
    'import os',
    'from datetime import date, timedelta',
    'from sqlalchemy import select',
    'from app import crud',
    'from app.database import AsyncSessionLocal',
    'from app.models import User, Team, DailySnippet, WeeklySnippet, StudentRiskSnapshot',
    '',
    'EMAIL = os.environ["E2E_PROF_STUDENT_EMAIL"]',
    'NAME = os.environ["E2E_PROF_STUDENT_NAME"]',
    '',
    'def monday_of(target: date) -> date:',
    '    return target - timedelta(days=target.weekday())',
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
    '',
    '        user_result = await db.execute(select(User).filter(User.email == EMAIL))',
    '        user = user_result.scalars().first()',
    '        if not user:',
    '            raise RuntimeError("Failed to resolve seeded student user")',
    '',
    '        team_result = await db.execute(select(Team).filter(Team.name == "E2E Professor Student Team"))',
    '        team = team_result.scalars().first()',
    '        if not team:',
    '            team = Team(name="E2E Professor Student Team", league_type="none")',
    '            db.add(team)',
    '            await db.flush()',
    '        user.team_id = team.id',
    '',
    '        today = date.today()',
    '        week_start = monday_of(today)',
    '',
    '        daily_result = await db.execute(',
    '            select(DailySnippet).filter(DailySnippet.user_id == user.id, DailySnippet.date == today)',
    '        )',
    '        daily = daily_result.scalars().first()',
    '        if not daily:',
    '            daily = DailySnippet(',
    '                user_id=user.id,',
    '                date=today,',
    '                content=f"[E2E-PROF-STUDENT-DAILY] {today.isoformat()}",',
    '                feedback=None,',
    '            )',
    '            db.add(daily)',
    '            await db.flush()',
    '        else:',
    '            daily.content = f"[E2E-PROF-STUDENT-DAILY] {today.isoformat()}"',
    '',
    '        weekly_result = await db.execute(',
    '            select(WeeklySnippet).filter(WeeklySnippet.user_id == user.id, WeeklySnippet.week == week_start)',
    '        )',
    '        weekly = weekly_result.scalars().first()',
    '        if not weekly:',
    '            weekly = WeeklySnippet(',
    '                user_id=user.id,',
    '                week=week_start,',
    '                content=f"[E2E-PROF-STUDENT-WEEKLY] {week_start.isoformat()}",',
    '                feedback=None,',
    '            )',
    '            db.add(weekly)',
    '            await db.flush()',
    '        else:',
    '            weekly.content = f"[E2E-PROF-STUDENT-WEEKLY] {week_start.isoformat()}"',
    '',
    '        snapshot = StudentRiskSnapshot(',
    '            user_id=user.id,',
    '            l1=92.0,',
    '            l2=94.0,',
    '            l3=88.0,',
    '            risk_score=93.5,',
    '            risk_band="Critical",',
    '            confidence={',
    '                "score": 0.95,',
    '                "data_coverage": 0.9,',
    '                "signal_agreement": 0.97,',
    '                "history_depth": 0.9,',
    '            },',
    '            reasons_json=[',
    '                {',
    '                    "layer": "L2",',
    '                    "risk_factor": "RF4_actionability",',
    '                    "prompt_items": ["action_translation", "next_action"],',
    '                    "severity": "high",',
    '                    "impact": 18.5,',
    '                    "evidence": "E2E seeded high risk actionability issue",',
    '                    "why_it_matters": "E2E seeded reason",',
    '                }',
    '            ],',
    '            tone_policy_json={',
    '                "primary": "질문",',
    '                "secondary": ["제안"],',
    '                "suppressed": ["훈계"],',
    '                "trigger_patterns": ["P5_strategy_mismatch"],',
    '                "policy_confidence": 0.9,',
    '            },',
    '            daily_subscores_json={"rubric_risk": 0.9},',
    '            weekly_subscores_json={"weekly_rubric_risk": 0.92},',
    '            trend_subscores_json={"m_trend_accel": 0.8},',
    '            needs_professor_review=True,',
    '        )',
    '        db.add(snapshot)',
    '',
    '        await db.commit()',
    '',
    '        print(json.dumps({',
    '            "user_id": user.id,',
    '            "user_name": user.name,',
    '            "user_email": user.email,',
    '            "daily_snippet_id": daily.id,',
    '            "weekly_snippet_id": weekly.id,',
    '        }))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  return runServerPython<SeedProfessorStudentResult>(script, {
    E2E_PROF_STUDENT_EMAIL: 'e2e-prof-student@gachon.ac.kr',
    E2E_PROF_STUDENT_NAME: 'E2E Professor Student',
  });
}

function bootstrapSignedSessionCookie(email: string, name: string): string {
  const script = [
    'import asyncio',
    'import base64',
    'import json',
    'import os',
    'from itsdangerous import TimestampSigner',
    'from app import crud',
    'from app.core.config import settings',
    'from app.database import AsyncSessionLocal',
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
    throw new Error('Signed session bootstrap did not return session_cookie');
  }

  return result.session_cookie;
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

async function assertProfessorSessionReady(page: Page): Promise<void> {
  const meResponse = await page.request.get(`${API_BASE}/auth/me`, {
    failOnStatusCode: false,
    headers: {
      cookie: `session=${ensureProfessorSessionCookie()}`,
    },
  });

  if (!meResponse.ok()) {
    throw new Error(`Professor session /auth/me failed: ${meResponse.status()} ${meResponse.statusText()}`);
  }

  const meBody = (await meResponse.json()) as {
    authenticated: boolean;
    user: null | { email?: string; roles?: string[] };
  };

  if (!meBody.authenticated) {
    throw new Error('Professor session is not authenticated');
  }

  const roles = meBody.user?.roles ?? [];
  if (!roles.includes('교수') && !roles.includes('gcs') && !roles.includes('admin')) {
    throw new Error(`Professor session has no privileged role: ${JSON.stringify(roles)}`);
  }
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

test.describe('Professor mentoring High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(() => {
    ensureServerSchemaReady();
  });

  test.beforeEach(async ({ page }) => {
    await setSessionCookieForApi(page, ensureProfessorSessionCookie());
    await assertProfessorSessionReady(page);
    await setupApiProxy(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-PROF-001] @high 교수 페이지 진입 + Risk Queue 렌더 + risk-evaluate 요청', async ({ page }) => {
    const seed = seedProfessorStudentFixture();

    await page.goto('/professor');
    await expect(page).toHaveURL(/\/professor/);

    await expect(page.getByRole('heading', { name: '교수 멘토링' })).toBeVisible();
    await expect(page.getByText('Risk Queue')).toBeVisible();

    const seededQueueButton = page.getByRole('button', { name: new RegExp(seed.user_name) }).first();
    await expect(seededQueueButton).toBeVisible();
    await seededQueueButton.click();

    const evaluateResponsePromise = page.waitForResponse(
      (res) =>
        res.url().includes(`/professor/students/${seed.user_id}/risk-evaluate`) &&
        res.request().method() === 'POST',
    );

    await page.getByRole('button', { name: 'risk-evaluate' }).click();

    const evaluateResponse = await evaluateResponsePromise;
    expect(evaluateResponse.ok()).toBeTruthy();

    await expect(page.getByText('추천 코멘트 탭 (자동 전송 없음)')).toBeVisible();
  });

  test('[CHK-PROF-002] @high 교수 코멘트 전송 시 comment_type=professor', async ({ page }) => {
    const seed = seedProfessorStudentFixture();

    await page.goto('/professor');
    await expect(page).toHaveURL(/\/professor/);

    const seededQueueButton = page.getByRole('button', { name: new RegExp(seed.user_name) }).first();
    await expect(seededQueueButton).toBeVisible();
    await seededQueueButton.click();

    await expect(page.getByRole('heading', { name: '선택 학생 스니펫 피드 (교수 코멘트)' })).toBeVisible();

    const weeklyTab = page.getByRole('tab', { name: '주간 스니펫' });
    const dailyTab = page.getByRole('tab', { name: '일간 스니펫' });
    if (await weeklyTab.isEnabled()) {
      await weeklyTab.click();
    } else {
      await dailyTab.click();
    }

    const commentsToggle = page.getByRole('button', { name: /댓글\s+\d+개/ }).first();
    await expect(commentsToggle).toBeVisible();
    await commentsToggle.click();

    const draft = `[CHK-PROF-002] professor comment ${Date.now()}`;
    const commentInput = page.getByPlaceholder('댓글을 남겨보세요... (Markdown 지원)').first();
    await expect(commentInput).toBeVisible();
    await commentInput.fill(draft);

    const createCommentResponsePromise = page.waitForResponse(
      (res) => res.url().includes('/comments') && res.request().method() === 'POST',
    );

    await page.locator('form').filter({ has: commentInput }).locator('button[type="submit"]').click();

    const createCommentResponse = await createCommentResponsePromise;
    expect(createCommentResponse.ok()).toBeTruthy();

    const createBody = (await createCommentResponse.json()) as {
      id: number;
      comment_type: string;
      content: string;
    };

    expect(createBody.id).toBeGreaterThan(0);
    expect(createBody.comment_type).toBe('professor');
    expect(createBody.content).toBe(draft);
  });

  test('[CHK-PROF-003] @high 비권한 세션의 professor API 접근 차단', async ({ playwright }) => {
    const sessionCookie = bootstrapSignedSessionCookie('e2e-outsider@example.com', 'E2E Outsider');

    const outsiderContext = await playwright.request.newContext({
      baseURL: API_BASE,
      failOnStatusCode: false,
      extraHTTPHeaders: {
        cookie: `session=${sessionCookie}`,
      },
    });

    try {
      const meRes = await outsiderContext.get('/auth/me');
      expect(meRes.status()).toBe(200);

      const meBody = (await meRes.json()) as {
        authenticated: boolean;
        user: null | { roles?: string[] };
      };

      expect(meBody.authenticated).toBeTruthy();
      expect(Array.isArray(meBody.user?.roles)).toBeTruthy();
      expect((meBody.user?.roles ?? []).includes('교수')).toBeFalsy();
      expect((meBody.user?.roles ?? []).includes('gcs')).toBeFalsy();
      expect((meBody.user?.roles ?? []).includes('admin')).toBeFalsy();

      const overviewRes = await outsiderContext.get('/professor/overview');
      expect(overviewRes.status()).toBe(403);

      const queueRes = await outsiderContext.get('/professor/risk-queue?limit=5');
      expect(queueRes.status()).toBe(403);
    } finally {
      await outsiderContext.dispose();
    }
  });

  test('[CHK-PROF-004] @high 교수는 팀이 달라도 학생 스니펫 조회 가능', async ({ playwright }) => {
    const seed = seedProfessorStudentFixture();

    const professorContext = await playwright.request.newContext({
      baseURL: API_BASE,
      failOnStatusCode: false,
      extraHTTPHeaders: {
        cookie: `session=${ensureProfessorSessionCookie()}`,
      },
    });

    try {
      const snippetRes = await professorContext.get(`/daily-snippets/${seed.daily_snippet_id}`);
      expect(snippetRes.ok()).toBeTruthy();

      const snippetBody = (await snippetRes.json()) as {
        id: number;
        user_id: number;
        editable: boolean;
        user?: {
          email?: string;
        };
      };

      expect(snippetBody.id).toBe(seed.daily_snippet_id);
      expect(snippetBody.user_id).toBe(seed.user_id);
      expect(snippetBody.user?.email).toBe(seed.user_email);
      expect(snippetBody.editable).toBeFalsy();
    } finally {
      await professorContext.dispose();
    }
  });
});
