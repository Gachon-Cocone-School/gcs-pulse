import { expect, test } from '@playwright/test';

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

test.describe('Achievements High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(async ({ request }) => {
    const meRes = await request.get(`${API_BASE}/auth/me`);
    expect(meRes.ok()).toBeTruthy();

    const meBody = (await meRes.json()) as {
      authenticated?: boolean;
      user?: {
        roles?: string[];
      } | null;
    };

    const roles = meBody.user?.roles ?? [];
    if (!roles.some((role) => role === 'gcs' || role === '교수' || role === 'admin')) {
      test.skip(true, 'Achievements high tests require privileged auth state');
    }
  });

  test.beforeEach(async ({ page, request }) => {
    const termsRes = await request.get(`${API_BASE}/terms`);
    expect(termsRes.ok()).toBeTruthy();

    const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;
    const requiredTerms = terms.filter((term) => term.is_required);

    if (requiredTerms.length > 0) {
      const csrfRes = await request.get(`${API_BASE}/auth/csrf`);
      expect(csrfRes.ok()).toBeTruthy();
      const csrfBody = (await csrfRes.json()) as { csrf_token: string };

      for (const term of requiredTerms) {
        const consentRes = await request.post(`${API_BASE}/consents`, {
          data: { term_id: term.id, agreed: true },
          headers: { 'x-csrf-token': csrfBody.csrf_token },
        });
        expect(consentRes.ok()).toBeTruthy();
      }
    }

    const meRes = await request.get(`${API_BASE}/achievements/me`);
    expect(meRes.ok()).toBeTruthy();
    const meBody = (await meRes.json()) as {
      items?: Array<{ code?: string; name?: string }>;
      total?: number;
    };
    const achievementItems = meBody.items ?? [];

    if (achievementItems.length === 0) {
      test.skip(true, 'CI seed has no achievement grants for bypass user');
    }

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

  test('[CHK-ACH-001] @high 업적 페이지 기본 노출', async ({ page }) => {
    await page.goto('/achievements');
    await expect(page).toHaveURL(/\/achievements/);

    await expect(page.getByRole('heading', { name: '내 업적' })).toBeVisible();
    await expect(page.getByText('획득한 업적을 업적별로 모아보고 지급 횟수와 최근 획득일을 확인하세요.')).toBeVisible();
  });

  test('[CHK-ACH-002] @high 업적 목록 카드/희귀도/횟수 노출', async ({ page }) => {
    await page.goto('/achievements');

    await expect(page.getByText('E2E 레전드 연속 달성')).toBeVisible();
    await expect(page.getByText('E2E 에픽 작성자')).toBeVisible();
    await expect(page.getByText('E2E 일반 시작')).toBeVisible();

    await expect(page.locator('span', { hasText: /^레전드$/ }).first()).toBeVisible();
    await expect(page.locator('span', { hasText: /^에픽$/ }).first()).toBeVisible();
    await expect(page.locator('span', { hasText: /^일반$/ }).first()).toBeVisible();

    const countBadges = page.locator('span', { hasText: /^x\d+$/ });
    await expect(countBadges.first()).toBeVisible();

    const legendCard = page.locator('li', { hasText: 'E2E 레전드 연속 달성' });
    const epicCard = page.locator('li', { hasText: 'E2E 에픽 작성자' });
    const commonCard = page.locator('li', { hasText: 'E2E 일반 시작' });

    await expect(legendCard).toBeVisible();
    await expect(epicCard).toBeVisible();
    await expect(commonCard).toBeVisible();
  });

  test('[CHK-ACH-003] @high 최근 업적 섹션 노출 및 희귀도 우선 정렬', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: '최근 업적' })).toBeVisible();

    const recentList = page.locator('section').filter({ hasText: '최근 업적' });
    await expect(recentList.getByText('E2E 레전드 연속 달성')).toBeVisible();
    await expect(recentList.getByText('E2E 에픽 작성자')).toBeVisible();
    await expect(recentList.getByText('E2E 일반 시작')).toBeVisible();

    const firstItemText = await recentList.locator('li').first().innerText();
    expect(firstItemText).toContain('E2E 레전드 연속 달성');
  });

  test('[CHK-ACH-004] @high 내 업적 API 응답 스키마/정렬 검증', async ({ page, request }) => {
    await page.goto('/achievements');

    const res = await request.get(`${API_BASE}/achievements/me`);
    expect(res.status()).toBe(200);

    const body = (await res.json()) as {
      items: Array<{
        code: string;
        name: string;
        rarity: string;
        grant_count: number;
        last_granted_at: string;
      }>;
      total: number;
    };

    expect(body.total).toBeGreaterThanOrEqual(3);

    const codes = body.items.map((item) => item.code);
    expect(codes).toContain('e2e_legend_streak');
    expect(codes).toContain('e2e_epic_writer');
    expect(codes).toContain('e2e_common_starter');

    const rarityRank: Record<string, number> = {
      legend: 5,
      epic: 4,
      rare: 3,
      uncommon: 2,
      common: 1,
    };

    for (let i = 1; i < body.items.length; i += 1) {
      const prev = body.items[i - 1];
      const curr = body.items[i];
      const prevRank = rarityRank[(prev.rarity || 'common').toLowerCase()] ?? 1;
      const currRank = rarityRank[(curr.rarity || 'common').toLowerCase()] ?? 1;
      expect(prevRank).toBeGreaterThanOrEqual(currRank);
    }
  });
});
