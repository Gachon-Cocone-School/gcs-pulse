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
      `${process.env.E2E_API_URL || 'http://127.0.0.1:8000'}/daily-snippets/${snippetId}?test_now=2026-02-20T10:00:00+09:00`,
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
  }) => {
    const apiBase = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

    const createBeforeResponse = await page.request.post(`${apiBase}/daily-snippets`, {
      data: { content: `[CHK-DAILY-003] before-create ${Date.now()}` },
      headers: {
        'content-type': 'application/json',
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
          'x-test-now': NOW_DAILY_AFTER_CUTOFF,
        },
      }
    );
    expect(updateAfterResponse.status()).toBe(403);

    await goToSnippetPage('daily', NOW_DAILY_AFTER_CUTOFF, beforeCreated.id);
    await expect(page.locator('#snippet-content')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '저장하기' })).toHaveCount(0);
  });
});
