import { test, expect } from '../fixtures/snippet-fixtures';

const NOW_OPEN = '2026-02-19T10:00:00+09:00';
const NOW_DAILY_BEFORE_CUTOFF = '2026-02-19T08:59:00+09:00';
const NOW_DAILY_AFTER_CUTOFF = '2026-02-19T09:00:00+09:00';

test.describe('Daily snippet High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test('[CHK-DAILY-001] @high Daily 기본 작성/수정/재조회 일치', async ({
    page,
    goToSnippetPage,
    fillSnippetAndSave,
    snippetTextarea,
  }) => {
    const initialContent = `[CHK-DAILY-001] initial ${Date.now()}`;
    const updatedContent = `[CHK-DAILY-001] updated ${Date.now()}`;

    await goToSnippetPage('daily', NOW_OPEN);
    await fillSnippetAndSave(initialContent);
    await expect(snippetTextarea).toHaveValue(initialContent);

    await fillSnippetAndSave(updatedContent);
    await expect(snippetTextarea).toHaveValue(updatedContent);

    await page.reload();
    await expect(snippetTextarea).toHaveValue(updatedContent);
  });

  test('[CHK-DAILY-002] @high 과거 Daily는 UI readOnly + 저장 시 403', async ({
    page,
    goToSnippetPage,
    snippetTextarea,
  }) => {
    const createdContent = `[CHK-DAILY-002] seed ${Date.now()}`;
    await goToSnippetPage('daily', NOW_OPEN);

    await snippetTextarea.fill(createdContent);
    const saveResponsePromise = page.waitForResponse((res) => {
      return (
        res.url().includes('/daily-snippets') &&
        (res.request().method() === 'POST' || res.request().method() === 'PUT')
      );
    });
    await page.getByRole('button', { name: '저장하기' }).click();
    const saveResponse = await saveResponsePromise;
    expect(saveResponse.ok()).toBeTruthy();

    const savedBody = (await saveResponse.json()) as { id: number };
    const snippetId = savedBody.id;

    await goToSnippetPage('daily', '2026-02-20T10:00:00+09:00', snippetId);
    await expect(page.locator('#snippet-content')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);

    const apiResponse = await page.request.put(
      `${process.env.E2E_API_URL || 'http://localhost:8000'}/daily-snippets/${snippetId}?test_now=2026-02-20T10:00:00+09:00`,
      {
        data: { content: '[CHK-DAILY-002] api forced edit attempt' },
        headers: {
          'content-type': 'application/json',
          'x-test-now': '2026-02-20T10:00:00+09:00',
        },
      }
    );
    expect(apiResponse.status()).toBe(403);
  });

  test('[CHK-DAILY-003] @high 08:59/09:00 컷오프 전후 편집 가능 날짜 전환', async ({
    goToSnippetPage,
    page,
    issueCsrfToken,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://localhost:8000';
    const csrfToken = await issueCsrfToken();

    const createBeforeResponse = await page.request.post(`${apiBase}/daily-snippets`, {
      data: { content: `[CHK-DAILY-003] before-create ${Date.now()}` },
      headers: {
        'content-type': 'application/json',
        'x-csrf-token': csrfToken,
        'x-test-now': NOW_DAILY_BEFORE_CUTOFF,
      },
    });
    expect(createBeforeResponse.ok()).toBeTruthy();

    const beforeCreated = (await createBeforeResponse.json()) as { id: number };

    await goToSnippetPage('daily', NOW_DAILY_BEFORE_CUTOFF, beforeCreated.id);
    await expect(page.locator('#snippet-content')).toBeVisible();

    const updateBeforeResponse = await page.request.put(
      `${apiBase}/daily-snippets/${beforeCreated.id}?test_now=${encodeURIComponent(NOW_DAILY_BEFORE_CUTOFF)}`,
      {
        data: { content: `[CHK-DAILY-003] before-update ${Date.now()}` },
        headers: {
          'content-type': 'application/json',
          'x-csrf-token': csrfToken,
          'x-test-now': NOW_DAILY_BEFORE_CUTOFF,
        },
      }
    );
    expect(updateBeforeResponse.status()).toBe(200);

    const updateAfterResponse = await page.request.put(
      `${apiBase}/daily-snippets/${beforeCreated.id}?test_now=${encodeURIComponent(NOW_DAILY_AFTER_CUTOFF)}`,
      {
        data: { content: `[CHK-DAILY-003] after-update ${Date.now()}` },
        headers: {
          'content-type': 'application/json',
          'x-csrf-token': csrfToken,
          'x-test-now': NOW_DAILY_AFTER_CUTOFF,
        },
      }
    );
    expect(updateAfterResponse.status()).toBe(403);

    await goToSnippetPage('daily', NOW_DAILY_AFTER_CUTOFF, beforeCreated.id);
    await expect(page.locator('#snippet-content')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);
  });

  test('[CHK-DAILY-004] @high 설정에서 발급한 API key로 Daily API 사용', async ({
    playwright,
    issueApiTokenFromSettings,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://localhost:8000';

    const rawToken = await issueApiTokenFromSettings(`[CHK-DAILY-004] ${Date.now()}`);

    const apiRequest = await playwright.request.newContext({
      baseURL: apiBase,
      failOnStatusCode: false,
      extraHTTPHeaders: {
        authorization: `Bearer ${rawToken}`,
        'content-type': 'application/json',
        'x-test-now': NOW_OPEN,
      },
    });

    try {
      const createdContent = `[CHK-DAILY-004] create ${Date.now()}`;
      const createResponse = await apiRequest.post('/daily-snippets', {
        data: { content: createdContent },
      });
      expect(createResponse.status()).toBe(200);

      const created = (await createResponse.json()) as { id: number; content: string };
      expect(created.id).toBeGreaterThan(0);
      expect(created.content).toBe(createdContent);

      const listResponse = await apiRequest.get('/daily-snippets');
      expect(listResponse.status()).toBe(200);
      const listBody = (await listResponse.json()) as {
        items: Array<{ id: number; content: string }>;
      };
      const listedSnippet = listBody.items.find((item) => item.id === created.id);
      expect(listedSnippet?.content).toBe(createdContent);

      const updatedContent = `[CHK-DAILY-004] update ${Date.now()}`;
      const updateResponse = await apiRequest.put(`/daily-snippets/${created.id}`, {
        data: { content: updatedContent },
      });
      expect(updateResponse.status()).toBe(200);

      const updated = (await updateResponse.json()) as { id: number; content: string };
      expect(updated.id).toBe(created.id);
      expect(updated.content).toBe(updatedContent);

      const getResponse = await apiRequest.get(`/daily-snippets/${created.id}`);
      expect(getResponse.status()).toBe(200);
      const fetched = (await getResponse.json()) as { id: number; content: string };
      expect(fetched.id).toBe(created.id);
      expect(fetched.content).toBe(updatedContent);
    } finally {
      await apiRequest.dispose();
    }
  });

  test('[CHK-DAILY-005] @high Daily organize 적용 후 본문 반영', async ({
    goToSnippetPage,
    fillSnippetAndSave,
    clickOrganizeAndApply,
    snippetTextarea,
  }) => {
    test.setTimeout(180_000);

    const sourceContent = `[CHK-DAILY-005] organize source ${Date.now()}`;

    await goToSnippetPage('daily', NOW_OPEN);
    await fillSnippetAndSave(sourceContent);

    await clickOrganizeAndApply();

    const afterValue = await snippetTextarea.inputValue();
    expect(afterValue.trim().length).toBeGreaterThan(0);
    expect(afterValue).not.toBe(sourceContent);
  });

  test('[CHK-DAILY-006] @high Daily feedback API 성공 응답', async ({
    goToSnippetPage,
    fillSnippetAndSave,
    clickFeedbackAndWait,
    snippetTextarea,
  }) => {
    test.setTimeout(180_000);

    const sourceContent = `[CHK-DAILY-006] feedback source ${Date.now()}`;

    await goToSnippetPage('daily', NOW_OPEN);
    await fillSnippetAndSave(sourceContent);

    await snippetTextarea.fill(`${sourceContent} (feedback trigger)`);
    await clickFeedbackAndWait();
  });

  test('[CHK-DAILY-007] @high Daily organize/feedback 취소 시 abort 에러 없이 복구', async ({
    page,
    goToSnippetPage,
    fillSnippetAndSave,
    snippetTextarea,
  }) => {
    test.setTimeout(180_000);

    const sourceContent = `[CHK-DAILY-007] cancel source ${Date.now()}`;
    const abortErrors: string[] = [];

    page.on('pageerror', (err) => {
      abortErrors.push(err.message);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        abortErrors.push(msg.text());
      }
    });

    await goToSnippetPage('daily', NOW_OPEN);
    await fillSnippetAndSave(sourceContent);

    await page.route(
      (url) =>
        url.toString().includes('/daily-snippets') &&
        url.toString().includes('/organize') &&
        url.toString().includes('stream=1'),
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        await route.fulfill({
          status: 200,
          headers: { 'content-type': 'text/event-stream' },
          body: 'event: done\ndata: {"organized_content":"cancel organize done"}\n\n',
        });
      }
    );

    await page.getByRole('button', { name: 'AI 제안' }).click();
    await expect(page.getByText('AI 정리 결과를 만들고 있어요')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: '취소하기' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'AI 제안' })).toBeEnabled();
    await page.unroute(
      (url) =>
        url.toString().includes('/daily-snippets') &&
        url.toString().includes('/organize') &&
        url.toString().includes('stream=1')
    );

    await snippetTextarea.fill(`${sourceContent} (feedback cancel)`);

    await page.route(
      (url) =>
        url.toString().includes('/daily-snippets') &&
        url.toString().includes('/feedback') &&
        url.toString().includes('stream=1'),
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        await route.fulfill({
          status: 200,
          headers: { 'content-type': 'text/event-stream' },
          body: 'event: done\ndata: {"feedback":"cancel feedback done"}\n\n',
        });
      }
    );

    await page.getByRole('button', { name: 'AI 채점' }).click();
    await expect(page.getByText('AI 피드백을 만들고 있어요')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: '취소' }).click();
    await expect(page.getByText('AI 피드백을 만들고 있어요')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'AI 채점' })).toBeEnabled();
    await page.unroute(
      (url) =>
        url.toString().includes('/daily-snippets') &&
        url.toString().includes('/feedback') &&
        url.toString().includes('stream=1')
    );

    expect(
      abortErrors.filter((line) => line.includes('signal is aborted without reason')),
      '취소 시 ApiError 래핑이 발생하면 안 됩니다.'
    ).toEqual([]);
  });

  test('[CHK-DAILY-008] @high 날짜 선택으로 과거 Daily 조회', async ({
    page,
    goToSnippetPage,
    issueCsrfToken,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://localhost:8000';
    const csrfToken = await issueCsrfToken();
    const seededContent = `[CHK-DAILY-008] seeded ${Date.now()}`;

    const createResponse = await page.request.post(`${apiBase}/daily-snippets`, {
      data: { content: seededContent },
      headers: {
        'content-type': 'application/json',
        'x-csrf-token': csrfToken,
        'x-test-now': '2026-02-18T10:00:00+09:00',
      },
    });
    expect(createResponse.ok()).toBeTruthy();

    await goToSnippetPage('daily', NOW_OPEN);

    const dateInput = page.getByLabel('일간 조회 날짜 선택');
    await expect(dateInput).toBeVisible();
    await dateInput.fill('2026-02-18');

    await expect(page).toHaveURL(/date=2026-02-18/);
    await expect(page.locator('main .prose')).toContainText(seededContent);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);
  });

  test('[CHK-DAILY-009] @high 미래 Daily 조회 입력은 오늘로 보정 + API 400', async ({
    page,
    goToSnippetPage,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://localhost:8000';

    await goToSnippetPage('daily', NOW_OPEN);

    const dateInput = page.getByLabel('일간 조회 날짜 선택');
    await expect(dateInput).toBeVisible();
    await dateInput.fill('2026-02-20');

    await expect(page).toHaveURL(/date=2026-02-19/);

    const futureResponse = await page.request.get(
      `${apiBase}/daily-snippets/page-data?date=2026-02-20&test_now=${encodeURIComponent(NOW_OPEN)}`,
      {
        headers: {
          'x-test-now': NOW_OPEN,
        },
      }
    );
    expect(futureResponse.status()).toBe(400);
  });
});
