import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');
const PROFESSOR_EMAIL = 'e2e-professor@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Professor';

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

  test.beforeEach(async ({ page }) => {
    await setSessionCookieForApi(page, ensureProfessorSessionCookie());
    await assertProfessorSessionReady(page);
    await setupApiProxy(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-PROF-001] @high /professor zero-base 페이지 표시', async ({ page }) => {
    await page.goto('/professor');
    await expect(page).toHaveURL(/\/professor/);
    await expect(page.getByRole('heading', { name: '교수 멘토링' })).toBeVisible();
    await expect(page.getByText('준비 중인 페이지입니다.')).toBeVisible();
  });

  test('[CHK-PROF-002] @high /professor에서 동료 피드백 하위 라우트 이동', async ({ page }) => {
    await page.goto('/professor');

    await page.getByRole('link', { name: '동료 피드백' }).click();
    await expect(page).toHaveURL(/\/professor\/peer-reviews/);
    await expect(page.getByRole('heading', { name: '동료 피드백' })).toBeVisible();
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

      const peerReviewsRes = await outsiderContext.get('/professor/peer-reviews/sessions');
      expect(peerReviewsRes.status()).toBe(403);
    } finally {
      await outsiderContext.dispose();
    }
  });
});
