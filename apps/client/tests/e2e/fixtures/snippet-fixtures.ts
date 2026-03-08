import { expect, type APIRequestContext, type Locator, test as base } from '@playwright/test';

const TEST_NOW_QUERY_KEY = 'test_now';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const LOCAL_API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));

function toLocalApiUrl(url: string): string {
  if (url.startsWith(REMOTE_API_ORIGIN)) {
    return url.replace(REMOTE_API_ORIGIN, LOCAL_API_ORIGIN);
  }
  return url;
}

async function issueCsrfTokenFromApi(request: APIRequestContext): Promise<string> {
  const csrfRes = await request.get(`${LOCAL_API_ORIGIN}/auth/csrf`);
  expect(csrfRes.ok()).toBeTruthy();

  const csrfBody = (await csrfRes.json()) as { csrf_token: string };
  expect(typeof csrfBody.csrf_token).toBe('string');
  expect(csrfBody.csrf_token).toBeTruthy();

  return csrfBody.csrf_token;
}

async function ensureRequiredConsentsFromApi(request: APIRequestContext): Promise<void> {
  const termsRes = await request.get(`${LOCAL_API_ORIGIN}/terms`);
  expect(termsRes.ok()).toBeTruthy();

  const terms = (await termsRes.json()) as Array<{ id: number; is_required: boolean }>;
  const requiredTermIds = new Set(terms.filter((term) => term.is_required).map((term) => term.id));
  expect(requiredTermIds.size).toBeGreaterThan(0);

  const meRes = await request.get(`${LOCAL_API_ORIGIN}/auth/me`);
  expect(meRes.ok()).toBeTruthy();
  const meBody = (await meRes.json()) as {
    user: null | {
      consents: Array<{ term_id: number }>;
    };
  };

  const agreedTermIds = new Set((meBody.user?.consents ?? []).map((consent) => consent.term_id));
  const missingTermIds: number[] = [];
  requiredTermIds.forEach((termId) => {
    if (!agreedTermIds.has(termId)) {
      missingTermIds.push(termId);
    }
  });

  if (missingTermIds.length === 0) {
    return;
  }

  const csrfToken = await issueCsrfTokenFromApi(request);

  for (const termId of missingTermIds) {
    const consentRes = await request.post(`${LOCAL_API_ORIGIN}/consents`, {
      data: { term_id: termId, agreed: true },
      headers: { 'x-csrf-token': csrfToken },
    });
    expect(consentRes.ok()).toBeTruthy();
  }
}

type SnippetKind = 'daily' | 'weekly';

type SnippetFixtures = {
  goToSnippetPage: (kind: SnippetKind, testNow: string, id?: number) => Promise<void>;
  fillSnippetAndSave: (content: string) => Promise<void>;
  issueApiTokenFromSettings: (description?: string) => Promise<string>;
  issueCsrfToken: () => Promise<string>;
  clickOrganizeAndApply: () => Promise<void>;
  clickFeedbackAndWait: () => Promise<void>;
  snippetTextarea: Locator;
};

export const test = base.extend<SnippetFixtures>({
  goToSnippetPage: async ({ page }, use) => {
    let apiProxyReady = false;

    const ensureApiProxy = async () => {
      if (apiProxyReady) return;

      await Promise.all(
        API_PROXY_ORIGINS.map((origin) =>
          page.route(`${origin}/**`, async (route) => {
            const request = route.request();
            const targetUrl = toLocalApiUrl(request.url());

            const headers = {
              ...request.headers(),
            };
            delete headers.host;

            const cookies = await page.context().cookies(LOCAL_API_ORIGIN);
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

      apiProxyReady = true;
    };

    await use(async (kind, testNow, id) => {
      await ensureApiProxy();

      const path = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
      const params = new URLSearchParams();
      params.set(TEST_NOW_QUERY_KEY, testNow);
      if (id != null) params.set('id', String(id));

      await page.goto(`${path}?${params.toString()}`);
      await expect(page).toHaveURL(new RegExp(`${path}\\?`));

      const editor = page.locator('#snippet-content');
      const preview = page.locator('main [role="tabpanel"] .prose');

      await expect
        .poll(async () => {
          const editorCount = await editor.count();
          const previewCount = await preview.count();
          return editorCount + previewCount;
        })
        .toBeGreaterThan(0);
    });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  },

  fillSnippetAndSave: async ({ page }, use) => {
    await use(async (content) => {
      const textarea = page.locator('#snippet-content');
      await expect(textarea).toBeVisible();
      await textarea.fill(content);

      const saveResponsePromise = page.waitForResponse((res) => {
        const url = res.url();
        return (
          (url.includes('/daily-snippets') || url.includes('/weekly-snippets')) &&
          (res.request().method() === 'POST' || res.request().method() === 'PUT')
        );
      });

      const saveButton = page.getByRole('button', { name: '저장하기' });
      await saveButton.click();
      const saveResponse = await saveResponsePromise;
      expect(saveResponse.ok()).toBeTruthy();

      await expect(saveButton).toBeEnabled();
      await expect(textarea).toHaveValue(content);
    });
  },

  issueApiTokenFromSettings: async ({ page, request }, use) => {
    await use(async (description = `e2e-token-${Date.now()}`) => {
      await Promise.all(
        API_PROXY_ORIGINS.map((origin) =>
          page.route(`${origin}/**`, async (route) => {
            const req = route.request();
            const targetUrl = toLocalApiUrl(req.url());

            const headers = {
              ...req.headers(),
            };
            delete headers.host;

            const cookies = await page.context().cookies(LOCAL_API_ORIGIN);
            if (cookies.length > 0) {
              headers.cookie = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
            }

            const response = await page.request.fetch(targetUrl, {
              method: req.method(),
              headers,
              data: req.postDataBuffer() ?? undefined,
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

      await ensureRequiredConsentsFromApi(request);

      await page.goto('/settings');
      await expect(page).toHaveURL(/\/settings/);

      const createButton = page.getByRole('button', { name: '새 토큰 생성' });
      await expect(createButton).toBeVisible();
      await createButton.click();

      const descriptionInput = page.locator('#description');
      await expect(descriptionInput).toBeVisible();
      await descriptionInput.fill(description);

      const createResponsePromise = page.waitForResponse((res) => {
        return res.url().includes('/auth/tokens') && res.request().method() === 'POST';
      });

      await page.getByRole('button', { name: '생성하기' }).click();

      const createResponse = await createResponsePromise;
      expect(createResponse.ok()).toBeTruthy();

      const body = (await createResponse.json()) as { token?: string };
      expect(typeof body.token).toBe('string');
      expect(body.token).toBeTruthy();

      await expect(page.getByText('토큰이 성공적으로 생성되었습니다')).toBeVisible();

      return body.token!;
    });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  },

  issueCsrfToken: async ({ request }, use) => {
    await use(async () => {
      const csrfRes = await request.get(`${LOCAL_API_ORIGIN}/auth/csrf`);
      expect(csrfRes.ok()).toBeTruthy();

      const csrfBody = (await csrfRes.json()) as { csrf_token: string };
      expect(typeof csrfBody.csrf_token).toBe('string');
      expect(csrfBody.csrf_token).toBeTruthy();

      return csrfBody.csrf_token;
    });
  },

  clickOrganizeAndApply: async ({ page }, use) => {
    await use(async () => {
      await page.getByRole('button', { name: 'AI 제안' }).click();

      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible({ timeout: 120_000 });
      await expect(page.getByRole('heading', { name: 'AI 정리 결과' })).toBeVisible({ timeout: 120_000 });

      const applyButton = page.getByRole('button', { name: '적용하기' });
      await expect(applyButton).toBeEnabled({ timeout: 120_000 });

      const resultPreview = dialog.locator('.prose');
      await expect(resultPreview).toBeVisible({ timeout: 120_000 });
      await expect(resultPreview).not.toBeEmpty({ timeout: 120_000 });

      const saveResponsePromise = page.waitForResponse((res) => {
        const url = res.url();
        return (
          (url.includes('/daily-snippets') || url.includes('/weekly-snippets')) &&
          (res.request().method() === 'POST' || res.request().method() === 'PUT')
        );
      });

      await applyButton.click();
      const saveResponse = await saveResponsePromise;
      expect(saveResponse.ok()).toBeTruthy();

      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'AI 제안' })).toBeEnabled({ timeout: 60_000 });
    });
  },

  clickFeedbackAndWait: async ({ page }, use) => {
    await use(async () => {
      const feedbackResponsePromise = page.waitForResponse((res) => {
        const url = res.url();
        return (
          (url.includes('/daily-snippets/feedback') || url.includes('/weekly-snippets/feedback')) &&
          res.request().method() === 'GET'
        );
      });

      await page.getByRole('button', { name: 'AI 채점' }).click();
      const feedbackResponse = await feedbackResponsePromise;
      expect(feedbackResponse.ok()).toBeTruthy();
    });
  },

  snippetTextarea: async ({ page }, use) => {
    await use(page.locator('#snippet-content'));
  },
});

export { expect };
