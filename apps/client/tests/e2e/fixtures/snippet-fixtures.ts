import { expect, type Locator, test as base } from '@playwright/test';

const TEST_NOW_QUERY_KEY = 'test_now';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'https://api-dev.1000.school';
const LOCAL_API_ORIGIN = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

type SnippetKind = 'daily' | 'weekly';

type SnippetFixtures = {
  goToSnippetPage: (kind: SnippetKind, testNow: string, id?: number) => Promise<void>;
  fillSnippetAndSave: (content: string) => Promise<void>;
  issueApiTokenFromSettings: (description?: string) => Promise<string>;
  snippetTextarea: Locator;
};

export const test = base.extend<SnippetFixtures>({
  goToSnippetPage: async ({ page }, use) => {
    let apiProxyReady = false;

    const ensureApiProxy = async () => {
      if (apiProxyReady) return;

      await page.route(`${REMOTE_API_ORIGIN}/**`, async (route) => {
        const request = route.request();
        const targetUrl = request.url().replace(REMOTE_API_ORIGIN, LOCAL_API_ORIGIN);

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
      });

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

  issueApiTokenFromSettings: async ({ page }, use) => {
    await use(async (description = `e2e-token-${Date.now()}`) => {
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
  },

  snippetTextarea: async ({ page }, use) => {
    await use(page.locator('#snippet-content'));
  },
});

export { expect };
