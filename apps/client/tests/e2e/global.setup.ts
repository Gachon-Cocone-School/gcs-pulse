import { existsSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import type { FullConfig } from '@playwright/test';
import { request, type APIRequestContext } from '@playwright/test';

const AUTH_STATE_PATH = 'tests/e2e/.auth/user.json';
const DEFAULT_E2E_EMAIL = process.env.E2E_TEST_EMAIL || 'test@example.com';
const DEFAULT_E2E_NAME = process.env.E2E_TEST_NAME || 'Test User';

type SessionBootstrapResult = {
  session_cookie: string;
};

async function waitForServer(apiBaseURL: string) {
  const ctx = await request.newContext({ baseURL: apiBaseURL });

  for (let i = 0; i < 20; i += 1) {
    try {
      const res = await ctx.get('/auth/me');
      if ([200, 401].includes(res.status())) {
        await ctx.dispose();
        return;
      }
    } catch {
      // retry
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  await ctx.dispose();
  throw new Error(`Server is not ready at ${apiBaseURL}`);
}

function cookieBaseDomain(apiBaseURL: string): string {
  const host = new URL(apiBaseURL).hostname;
  return host === 'localhost' ? '127.0.0.1' : host;
}

function resolveServerRoot(): string {
  return resolve(process.cwd(), '../server');
}

function resolveServerPythonExecutable(serverRoot: string): string {
  if (process.env.E2E_SERVER_PYTHON) {
    return process.env.E2E_SERVER_PYTHON;
  }

  const venvPython = resolve(serverRoot, 'venv/bin/python');
  if (existsSync(venvPython)) {
    return venvPython;
  }

  return 'python3';
}

function bootstrapSignedSessionCookie(email: string, name: string): string {
  const serverRoot = resolveServerRoot();
  const pythonExecutable = resolveServerPythonExecutable(serverRoot);
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
    'EMAIL = os.environ["E2E_FALLBACK_EMAIL"]',
    'NAME = os.environ["E2E_FALLBACK_NAME"]',
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

  const result = spawnSync(pythonExecutable, ['-c', script], {
    cwd: serverRoot,
    encoding: 'utf-8',
    env: {
      ...process.env,
      PYTHONPATH: serverRoot,
      E2E_FALLBACK_EMAIL: email,
      E2E_FALLBACK_NAME: name,
    },
  });

  if (result.error) {
    throw new Error(`Failed to bootstrap fallback session: ${result.error.message}`);
  }

  if (result.status !== 0) {
    throw new Error(
      `Failed to bootstrap fallback session (exit ${result.status}): ${(result.stderr || result.stdout || '').trim()}`
    );
  }

  const output = result.stdout
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .at(-1);

  if (!output) {
    throw new Error('Fallback session bootstrap returned empty output');
  }

  const parsed = JSON.parse(output) as SessionBootstrapResult;
  if (!parsed.session_cookie) {
    throw new Error('Fallback session bootstrap did not return session_cookie');
  }

  return parsed.session_cookie;
}

async function writeFallbackAuthState(apiBaseURL: string) {
  const now = Math.floor(Date.now() / 1000);
  const sessionCookie = bootstrapSignedSessionCookie(DEFAULT_E2E_EMAIL, DEFAULT_E2E_NAME);

  const authState = {
    cookies: [
      {
        name: 'session',
        value: sessionCookie,
        domain: cookieBaseDomain(apiBaseURL),
        path: '/',
        expires: now + 14 * 24 * 60 * 60,
        httpOnly: true,
        secure: new URL(apiBaseURL).protocol === 'https:',
        sameSite: 'Lax' as const,
      },
    ],
    origins: [],
  };

  await mkdir(dirname(AUTH_STATE_PATH), { recursive: true });
  await writeFile(AUTH_STATE_PATH, JSON.stringify(authState, null, 2));
}

async function assertAuthenticatedState(apiBaseURL: string) {
  const verifyCtx = await request.newContext({
    baseURL: apiBaseURL,
    storageState: AUTH_STATE_PATH,
  });

  try {
    const meRes = await verifyCtx.get('/auth/me');
    if (meRes.status() !== 200) {
      throw new Error(`Auth state is not authenticated: ${meRes.status()} ${meRes.statusText()}`);
    }
  } finally {
    await verifyCtx.dispose();
  }
}

async function trySeedViaAuthCallback(seedCtx: APIRequestContext): Promise<{ ok: boolean; reason: string }> {
  const callbackAttempts = [
    '/auth/google/callback',
    `/auth/google/callback?test_email=${encodeURIComponent(DEFAULT_E2E_EMAIL)}&test_name=${encodeURIComponent(DEFAULT_E2E_NAME)}`,
  ];
  const failures: string[] = [];

  for (const endpoint of callbackAttempts) {
    try {
      const seedRes = await seedCtx.get(endpoint, { maxRedirects: 0 });
      if ([200, 302, 307].includes(seedRes.status())) {
        return { ok: true, reason: `callback success: ${endpoint}` };
      }
      failures.push(`callback failed: ${endpoint} -> ${seedRes.status()} ${seedRes.statusText()}`);
    } catch (error) {
      failures.push(`callback error: ${endpoint} -> ${(error as Error).message}`);
    }
  }

  return {
    ok: false,
    reason: failures.join(' | ') || 'callback attempt not executed',
  };
}

async function seedBypassUserAndSaveAuthState(apiBaseURL: string) {
  const seedCtx = await request.newContext({ baseURL: apiBaseURL });

  try {
    const callbackSeed = await trySeedViaAuthCallback(seedCtx);

    if (callbackSeed.ok) {
      await mkdir(dirname(AUTH_STATE_PATH), { recursive: true });
      await seedCtx.storageState({ path: AUTH_STATE_PATH });
    } else {
      console.warn(`[e2e] ${callbackSeed.reason}; using signed-session fallback`);
      await writeFallbackAuthState(apiBaseURL);
    }

    await assertAuthenticatedState(apiBaseURL);
  } finally {
    await seedCtx.dispose();
  }
}

export default async function globalSetup(_config: FullConfig) {
  const apiBaseURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

  await waitForServer(apiBaseURL);
  await seedBypassUserAndSaveAuthState(apiBaseURL);
}
