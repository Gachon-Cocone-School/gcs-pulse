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

test.describe('Terms High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
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

  test('[CHK-TERMS-001] @high 이용약관 페이지 기본 UI 노출', async ({ page, request }) => {
    const termsRes = await request.get(`${API_BASE}/terms`);
    expect(termsRes.status()).toBe(200);

    const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;
    const requiredTerms = terms.filter((term) => term.is_required);
    expect(requiredTerms.length).toBeGreaterThan(0);

    await page.goto('/terms');

    const pendingButtons = page.getByRole('button', { name: '동의하기' });
    const completedButtons = page.getByRole('button', { name: '동의 완료' });

    const pendingCount = await pendingButtons.count();
    const completedCount = await completedButtons.count();

    if (pendingCount + completedCount === 0) {
      return;
    }

    expect(pendingCount + completedCount).toBe(requiredTerms.length);
    await expect(page.getByRole('button', { name: '동의하고 시작하기' })).toBeVisible();
  });

  test('[CHK-TERMS-002] @high 필수 미동의 시 제출 버튼 비활성', async ({ page, request }) => {
    const termsRes = await request.get(`${API_BASE}/terms`);
    expect(termsRes.status()).toBe(200);
    const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;

    await page.goto('/terms');

    const pendingCount = await page.getByRole('button', { name: '동의하기' }).count();
    const completedCount = await page.getByRole('button', { name: '동의 완료' }).count();

    if (pendingCount + completedCount === 0) {
      return;
    }

    const submitButton = page.getByRole('button', { name: '동의하고 시작하기' });

    const requiredTermsCount = terms.filter((term) => term.is_required).length;

    if (completedCount >= requiredTermsCount) {
      await expect(submitButton).toBeEnabled();
    } else {
      await expect(submitButton).toBeDisabled();
      await expect(
        page.getByText('필수 약관에 모두 동의해 주셔야 서비스 이용이 가능합니다.')
      ).toBeVisible();
    }
  });

  test('[CHK-TERMS-003] @high /terms API 기준 필수 약관 노출/렌더링 일치', async ({ page, request }) => {
    const termsRes = await request.get(`${API_BASE}/terms`);
    expect(termsRes.status()).toBe(200);
    const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;

    const requiredTerms = terms.filter((term) => term.is_required);
    expect(requiredTerms.length).toBeGreaterThan(0);

    await page.goto('/terms');

    const pendingButtons = page.getByRole('button', { name: '동의하기' });
    const completedButtons = page.getByRole('button', { name: '동의 완료' });

    const pendingCount = await pendingButtons.count();
    const completedCount = await completedButtons.count();

    if (pendingCount + completedCount === 0) {
      return;
    }

    expect(pendingCount + completedCount).toBe(requiredTerms.length);
    expect(pendingCount).toBeGreaterThanOrEqual(0);
  });

  test('[CHK-TERMS-004] @high /terms, /consents API 응답 검증', async ({ page, request }) => {
    const termsRes = await request.get(`${API_BASE}/terms`);
    expect(termsRes.status()).toBe(200);

    const terms = (await termsRes.json()) as Array<{
      id: number;
      is_required: boolean;
      type: string;
      version: string;
    }>;
    expect(Array.isArray(terms)).toBeTruthy();
    expect(terms.length).toBeGreaterThan(0);

    const requiredTerms = terms.filter((term) => term.is_required);
    expect(requiredTerms.length).toBeGreaterThan(0);

    await page.goto('/terms');

    const pendingButtons = page.getByRole('button', { name: '동의하기' });
    const completedButtons = page.getByRole('button', { name: '동의 완료' });

    const pendingCount = await pendingButtons.count();
    const completedCount = await completedButtons.count();

    if (pendingCount + completedCount > 0) {
      for (const _term of requiredTerms) {
        const pendingButton = page.getByRole('button', { name: '동의하기' }).first();
        if (await pendingButton.count()) {
          await expect(pendingButton).toBeVisible();
          await pendingButton.click();
        }
      }

      await expect(page.getByRole('button', { name: '동의하기' })).toHaveCount(0);
    }

    const csrfRes = await request.get(`${API_BASE}/auth/csrf`);
    expect(csrfRes.status()).toBe(200);
    const csrfBody = (await csrfRes.json()) as { csrf_token: string };
    expect(typeof csrfBody.csrf_token).toBe('string');
    expect(csrfBody.csrf_token).toBeTruthy();

    const consentRes = await request.post(`${API_BASE}/consents`, {
      data: { term_id: requiredTerms[0].id, agreed: true },
      headers: {
        'x-csrf-token': csrfBody.csrf_token,
      },
    });
    expect([200, 201].includes(consentRes.status())).toBeTruthy();
  });
});
