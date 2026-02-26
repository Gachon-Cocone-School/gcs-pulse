import { test, expect } from '../fixtures/snippet-fixtures';

const NOW_OPEN = '2026-02-19T10:00:00+09:00';
const NOW_WEEK_BEFORE_CUTOFF = '2026-02-23T08:59:00+09:00';
const NOW_WEEK_AFTER_CUTOFF = '2026-02-23T09:00:00+09:00';

test.describe('Weekly snippet High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test('[CHK-WEEKLY-001] @high Weekly 기본 작성/수정/재조회 일치', async ({
    page,
    goToSnippetPage,
    fillSnippetAndSave,
    snippetTextarea,
  }) => {
    const initialContent = `[CHK-WEEKLY-001] initial ${Date.now()}`;
    const updatedContent = `[CHK-WEEKLY-001] updated ${Date.now()}`;

    await goToSnippetPage('weekly', NOW_OPEN);
    await fillSnippetAndSave(initialContent);
    await expect(snippetTextarea).toHaveValue(initialContent);

    await fillSnippetAndSave(updatedContent);
    await expect(snippetTextarea).toHaveValue(updatedContent);

    await page.reload();
    await expect(snippetTextarea).toHaveValue(updatedContent);
  });

  test('[CHK-WEEKLY-002] @high 과거 Weekly는 UI readOnly + 저장 시 403', async ({
    page,
    goToSnippetPage,
    snippetTextarea,
  }) => {
    const createdContent = `[CHK-WEEKLY-002] seed ${Date.now()}`;
    await goToSnippetPage('weekly', '2026-02-17T10:00:00+09:00');

    await snippetTextarea.fill(createdContent);
    const saveResponsePromise = page.waitForResponse((res) => {
      return (
        res.url().includes('/weekly-snippets') &&
        (res.request().method() === 'POST' || res.request().method() === 'PUT')
      );
    });
    await page.getByRole('button', { name: '저장하기' }).click();
    const saveResponse = await saveResponsePromise;
    expect(saveResponse.ok()).toBeTruthy();

    const savedBody = (await saveResponse.json()) as { id: number };
    const snippetId = savedBody.id;

    await goToSnippetPage('weekly', '2026-02-23T10:00:00+09:00', snippetId);
    await expect(page.locator('#snippet-content')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);

    const apiResponse = await page.request.put(
      `${process.env.E2E_API_URL || 'http://127.0.0.1:8000'}/weekly-snippets/${snippetId}?test_now=2026-02-23T10:00:00+09:00`,
      {
        data: { content: '[CHK-WEEKLY-002] api forced edit attempt' },
        headers: {
          'content-type': 'application/json',
          'x-test-now': '2026-02-23T10:00:00+09:00',
        },
      }
    );
    expect(apiResponse.status()).toBe(403);
  });

  test('[CHK-WEEKLY-003] @high 월요일 09:00 전후 편집 가능 주차 전환', async ({
    goToSnippetPage,
    page,
    issueCsrfToken,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://127.0.0.1:8000';
    const csrfToken = await issueCsrfToken();

    const createBeforeResponse = await page.request.post(`${apiBase}/weekly-snippets`, {
      data: { content: `[CHK-WEEKLY-003] before-create ${Date.now()}` },
      headers: {
        'content-type': 'application/json',
        'x-csrf-token': csrfToken,
        'x-test-now': NOW_WEEK_BEFORE_CUTOFF,
      },
    });
    expect(createBeforeResponse.ok()).toBeTruthy();

    const beforeCreated = (await createBeforeResponse.json()) as { id: number };

    await goToSnippetPage('weekly', NOW_WEEK_BEFORE_CUTOFF, beforeCreated.id);
    await expect(page.locator('#snippet-content')).toBeVisible();

    const updateBeforeResponse = await page.request.put(
      `${apiBase}/weekly-snippets/${beforeCreated.id}?test_now=${encodeURIComponent(NOW_WEEK_BEFORE_CUTOFF)}`,
      {
        data: { content: `[CHK-WEEKLY-003] before-update ${Date.now()}` },
        headers: {
          'content-type': 'application/json',
          'x-csrf-token': csrfToken,
          'x-test-now': NOW_WEEK_BEFORE_CUTOFF,
        },
      }
    );
    expect(updateBeforeResponse.status()).toBe(200);

    const updateAfterResponse = await page.request.put(
      `${apiBase}/weekly-snippets/${beforeCreated.id}?test_now=${encodeURIComponent(NOW_WEEK_AFTER_CUTOFF)}`,
      {
        data: { content: `[CHK-WEEKLY-003] after-update ${Date.now()}` },
        headers: {
          'content-type': 'application/json',
          'x-csrf-token': csrfToken,
          'x-test-now': NOW_WEEK_AFTER_CUTOFF,
        },
      }
    );
    expect(updateAfterResponse.status()).toBe(403);

    await goToSnippetPage('weekly', NOW_WEEK_AFTER_CUTOFF, beforeCreated.id);
    await expect(page.locator('#snippet-content')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);
  });

  test('[CHK-WEEKLY-004] @high 설정에서 발급한 API key로 Weekly API 사용', async ({
    playwright,
    issueApiTokenFromSettings,
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

    const rawToken = await issueApiTokenFromSettings(`[CHK-WEEKLY-004] ${Date.now()}`);

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
      const createdContent = `[CHK-WEEKLY-004] create ${Date.now()}`;
      const createResponse = await apiRequest.post('/weekly-snippets', {
        data: { content: createdContent },
      });
      expect(createResponse.status()).toBe(200);

      const created = (await createResponse.json()) as { id: number; content: string };
      expect(created.id).toBeGreaterThan(0);
      expect(created.content).toBe(createdContent);

      const listResponse = await apiRequest.get('/weekly-snippets');
      expect(listResponse.status()).toBe(200);
      const listBody = (await listResponse.json()) as {
        items: Array<{ id: number; content: string }>;
      };
      const listedSnippet = listBody.items.find((item) => item.id === created.id);
      expect(listedSnippet?.content).toBe(createdContent);

      const updatedContent = `[CHK-WEEKLY-004] update ${Date.now()}`;
      const updateResponse = await apiRequest.put(`/weekly-snippets/${created.id}`, {
        data: { content: updatedContent },
      });
      expect(updateResponse.status()).toBe(200);

      const updated = (await updateResponse.json()) as { id: number; content: string };
      expect(updated.id).toBe(created.id);
      expect(updated.content).toBe(updatedContent);

      const getResponse = await apiRequest.get(`/weekly-snippets/${created.id}`);
      expect(getResponse.status()).toBe(200);
      const fetched = (await getResponse.json()) as { id: number; content: string };
      expect(fetched.id).toBe(created.id);
      expect(fetched.content).toBe(updatedContent);
    } finally {
      await apiRequest.dispose();
    }
  });

  test('[CHK-WEEKLY-005] @high Weekly organize 적용 후 본문 반영', async ({
    goToSnippetPage,
    fillSnippetAndSave,
    clickOrganizeAndApply,
    snippetTextarea,
  }) => {
    test.setTimeout(180_000);

    const sourceContent = `[CHK-WEEKLY-005] organize source ${Date.now()}`;

    await goToSnippetPage('weekly', NOW_OPEN);
    await fillSnippetAndSave(sourceContent);

    await clickOrganizeAndApply();

    const afterValue = await snippetTextarea.inputValue();
    expect(afterValue.trim().length).toBeGreaterThan(0);
    expect(afterValue).not.toBe(sourceContent);
  });

  test('[CHK-WEEKLY-006] @high Weekly feedback API 성공 응답', async ({
    goToSnippetPage,
    fillSnippetAndSave,
    clickFeedbackAndWait,
    snippetTextarea,
  }) => {
    test.setTimeout(180_000);

    const sourceContent = `[CHK-WEEKLY-006] feedback source ${Date.now()}`;

    await goToSnippetPage('weekly', NOW_OPEN);
    await fillSnippetAndSave(sourceContent);

    await snippetTextarea.fill(`${sourceContent} (feedback trigger)`);
    await clickFeedbackAndWait();
  });
});
