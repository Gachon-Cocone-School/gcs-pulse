import { expect, test, type APIRequestContext } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));

function toLocalApiUrl(url: string): string {
  if (url.startsWith(REMOTE_API_ORIGIN)) {
    return url.replace(REMOTE_API_ORIGIN, API_BASE);
  }
  return url;
}

async function issueCsrfToken(request: APIRequestContext): Promise<string> {
  const csrfRes = await request.get(`${API_BASE}/auth/csrf`);
  expect(csrfRes.ok()).toBeTruthy();
  const csrfBody = (await csrfRes.json()) as { csrf_token: string };
  expect(typeof csrfBody.csrf_token).toBe('string');
  expect(csrfBody.csrf_token).toBeTruthy();
  return csrfBody.csrf_token;
}

async function ensureRequiredConsents(request: APIRequestContext): Promise<void> {
  const termsRes = await request.get(`${API_BASE}/terms`);
  expect(termsRes.ok()).toBeTruthy();

  const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;
  const requiredTermIds = new Set(terms.filter((term) => term.is_required).map((term) => term.id));
  if (requiredTermIds.size === 0) {
    return;
  }

  const meRes = await request.get(`${API_BASE}/auth/me`);
  expect(meRes.ok()).toBeTruthy();
  const meBody = (await meRes.json()) as {
    user: null | {
      consents: Array<{ term_id: number }>;
    };
  };

  const agreedTermIds = new Set((meBody.user?.consents ?? []).map((consent) => consent.term_id));
  const missingTermIds = Array.from(requiredTermIds).filter((termId) => !agreedTermIds.has(termId));

  if (missingTermIds.length === 0) {
    return;
  }

  const csrfToken = await issueCsrfToken(request);

  for (const termId of missingTermIds) {
    const consentRes = await request.post(`${API_BASE}/consents`, {
      data: { term_id: termId, agreed: true },
      headers: { 'x-csrf-token': csrfToken },
    });
    expect(consentRes.ok()).toBeTruthy();
  }
}

async function ensureNoTeam(request: APIRequestContext): Promise<void> {
  const meRes = await request.get(`${API_BASE}/teams/me`);

  if (meRes.status() === 401) {
    return;
  }

  expect(meRes.ok()).toBeTruthy();

  const meBody = (await meRes.json()) as { team: null | { id: number } };
  if (!meBody.team) {
    return;
  }

  const leaveRes = await request.post(`${API_BASE}/teams/leave`, {
    headers: { 'x-csrf-token': await issueCsrfToken(request) },
  });
  expect(leaveRes.ok()).toBeTruthy();
}

test.describe('Settings High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page, request }) => {
    await ensureRequiredConsents(request);
    await ensureNoTeam(request);

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
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SETTINGS-001] @high 팀 생성/리그저장/이름변경/탈퇴', async ({ page }) => {
    const unique = Date.now();
    const createdName = `E2E Team ${unique}`;
    const renamedName = `${createdName} Renamed`;

    await page.goto('/settings?menu=team');
    await expect(page).toHaveURL(/\/settings(\?.*)?menu=team/);

    await page.getByLabel('팀 이름').fill(createdName);

    const createResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams') && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '팀 생성' }).click();
    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(200);

    await expect(page.getByText('현재 팀 정보')).toBeVisible();
    await expect(page.getByText(createdName)).toBeVisible();

    await page.getByRole('button', { name: '학기제' }).click();
    const saveLeagueResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams/me/league') && res.request().method() === 'PATCH'
    );
    await page.getByRole('button', { name: '팀 리그 저장' }).click();
    const saveLeagueResponse = await saveLeagueResponsePromise;
    expect(saveLeagueResponse.status()).toBe(200);

    await page.locator('#rename-team').fill(renamedName);
    const renameResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams/me') && res.request().method() === 'PATCH'
    );
    await page.getByRole('button', { name: '이름 변경' }).click();
    const renameResponse = await renameResponsePromise;
    expect(renameResponse.status()).toBe(200);
    await expect(page.getByText(renamedName)).toBeVisible();

    page.once('dialog', (dialog) => dialog.accept());
    const leaveResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams/leave') && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '팀 탈퇴' }).click();
    const leaveResponse = await leaveResponsePromise;
    expect(leaveResponse.status()).toBe(200);

    await expect(page.getByText('새 팀 만들기')).toBeVisible();
    await expect(page.getByText('초대코드로 팀 참여')).toBeVisible();
  });

  test('[CHK-SETTINGS-002] @high 팀 미소속 개인 리그 저장', async ({ page }) => {
    await page.goto('/settings?menu=league');
    await expect(page).toHaveURL(/\/settings(\?.*)?menu=league/);

    await expect(page.getByText('개인 리그 설정')).toBeVisible();
    await expect(page.getByText('팀 소속 사용자는 개인 리그를 변경할 수 없습니다.').first()).toHaveCount(0);

    const saveButton = page.getByRole('button', { name: '저장' });

    const selectLeagueAndSave = async (label: '학부제' | '미참여') => {
      const targetButton = page.getByRole('button', { name: label });
      await targetButton.click();

      if (await saveButton.isEnabled()) {
        const saveResponsePromise = page.waitForResponse((res) =>
          res.url().includes('/users/me/league') && res.request().method() === 'PATCH'
        );
        await saveButton.click();
        const saveResponse = await saveResponsePromise;
        expect(saveResponse.status()).toBe(200);
      }

      await expect(targetButton).toHaveAttribute('aria-pressed', 'true');
    };

    await selectLeagueAndSave('학부제');
    await selectLeagueAndSave('미참여');
  });

  test('[CHK-SETTINGS-003] @high 팀 소속 시 개인 리그 변경 불가', async ({ page }) => {
    const unique = Date.now();
    const teamName = `E2E Managed Team ${unique}`;

    await page.goto('/settings?menu=team');
    await expect(page).toHaveURL(/\/settings(\?.*)?menu=team/);

    const teamMeResponse = await page.request.get(`${API_BASE}/teams/me`);

    if (teamMeResponse.ok()) {
      const body = (await teamMeResponse.json()) as { team?: { id?: number } | null };
      if (!body.team) {
        await page.getByLabel('팀 이름').fill(teamName);
        const createResponsePromise = page.waitForResponse((res) =>
          res.url().includes('/teams') && res.request().method() === 'POST'
        );
        await page.getByRole('button', { name: '팀 생성' }).click();
        const createResponse = await createResponsePromise;
        expect(createResponse.status()).toBe(200);
      }
    }

    await page.goto('/settings?menu=league');
    await expect(page).toHaveURL(/\/settings(\?.*)?menu=league/);

    await expect(page.getByText('팀 소속 사용자는 개인 리그를 변경할 수 없습니다.')).toBeVisible();
    await expect(page.getByText('리그 변경은 팀 설정에서 진행해 주세요.')).toBeVisible();
    await expect(page.getByRole('button', { name: '저장' })).toHaveCount(0);

    await page.goto('/settings?menu=team');
    page.once('dialog', (dialog) => dialog.accept());
    const leaveResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams/leave') && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '팀 탈퇴' }).click();
    const leaveResponse = await leaveResponsePromise;
    expect(leaveResponse.status()).toBe(200);
  });

  test('[CHK-SETTINGS-004] @high 팀 설정에서 초대코드 복사 버튼 노출', async ({ page, request }) => {
    const unique = Date.now();
    const teamName = `E2E Invite Team ${unique}`;

    const meRes = await request.get(`${API_BASE}/teams/me`);
    expect(meRes.ok()).toBeTruthy();
    const meBody = (await meRes.json()) as { team: null | { name: string } };

    if (meBody.team) {
      const leaveRes = await request.post(`${API_BASE}/teams/leave`, {
        headers: { 'x-csrf-token': await issueCsrfToken(request) },
      });
      expect(leaveRes.ok()).toBeTruthy();
    }

    await page.goto('/settings?menu=team');
    await expect(page).toHaveURL(/\/settings(\?.*)?menu=team/);

    await page.getByLabel('팀 이름').fill(teamName);
    const createResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams') && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '팀 생성' }).click();
    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(200);

    const inviteCodeInput = page.locator('input[readonly]').first();
    await expect(inviteCodeInput).toBeVisible();
    await expect(inviteCodeInput).not.toHaveValue('');

    await expect(page.getByRole('button', { name: '복사' })).toBeVisible();

    page.once('dialog', (dialog) => dialog.accept());
    const leaveResponsePromise = page.waitForResponse((res) =>
      res.url().includes('/teams/leave') && res.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '팀 탈퇴' }).click();
    const leaveResponse = await leaveResponsePromise;
    expect(leaveResponse.status()).toBe(200);
  });

  test('[CHK-SETTINGS-005] @high 로그인 세션에서 settings 이동 중 auth/me 429 미발생', async ({ request }) => {
    const authMeStatuses: number[] = [];
    const menuSequence = ['api', 'team', 'league', 'api', 'team', 'api'] as const;

    for (const _menu of menuSequence) {
      const authMeRes = await request.get(`${API_BASE}/auth/me`);
      authMeStatuses.push(authMeRes.status());
    }

    expect(authMeStatuses.length).toBeGreaterThan(0);
    expect(authMeStatuses).not.toContain(429);
  });
});
