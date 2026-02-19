import { mkdir } from 'node:fs/promises';
import type { FullConfig } from '@playwright/test';
import { request } from '@playwright/test';

const AUTH_STATE_PATH = 'tests/e2e/.auth/user.json';

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

async function seedBypassUserAndSaveAuthState(apiBaseURL: string) {
  const seedCtx = await request.newContext({ baseURL: apiBaseURL });

  const seedRes = await seedCtx.get('/auth/google/callback', { maxRedirects: 0 });
  if (![200, 302, 307].includes(seedRes.status())) {
    throw new Error(`Failed to seed bypass user: ${seedRes.status()} ${seedRes.statusText()}`);
  }

  await mkdir('tests/e2e/.auth', { recursive: true });
  await seedCtx.storageState({ path: AUTH_STATE_PATH });
  await seedCtx.dispose();
}

export default async function globalSetup(_config: FullConfig) {
  const apiBaseURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

  await waitForServer(apiBaseURL);
  await seedBypassUserAndSaveAuthState(apiBaseURL);
}
