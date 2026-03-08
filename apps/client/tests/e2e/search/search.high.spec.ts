import { test, expect } from '@playwright/test';

const LOCAL_API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));

const NOW = '2026-02-19T10:00:00+09:00';

function toLocalApiUrl(url: string): string {
  if (url.startsWith(REMOTE_API_ORIGIN)) {
    return url.replace(REMOTE_API_ORIGIN, LOCAL_API_ORIGIN);
  }
  return url;
}

async function setupApiProxy(page: import('@playwright/test').Page) {
  await Promise.all(
    API_PROXY_ORIGINS.map((origin) =>
      page.route(`${origin}/**`, async (route) => {
        const request = route.request();
        const targetUrl = toLocalApiUrl(request.url());
        const headers = { ...request.headers() };
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
}

async function getCsrfToken(page: import('@playwright/test').Page): Promise<string> {
  const csrfRes = await page.request.get(`${LOCAL_API_ORIGIN}/auth/csrf`);
  expect(csrfRes.ok()).toBeTruthy();
  const body = (await csrfRes.json()) as { csrf_token: string };
  return body.csrf_token;
}

async function createDailySnippet(
  page: import('@playwright/test').Page,
  content: string,
  csrfToken: string,
): Promise<number> {
  const res = await page.request.post(`${LOCAL_API_ORIGIN}/daily-snippets`, {
    data: { content },
    headers: {
      'content-type': 'application/json',
      'x-csrf-token': csrfToken,
      'x-test-now': NOW,
    },
  });
  expect(res.ok()).toBeTruthy();
  const body = (await res.json()) as { id: number };
  return body.id;
}

async function createWeeklySnippet(
  page: import('@playwright/test').Page,
  content: string,
  csrfToken: string,
): Promise<number> {
  const res = await page.request.post(`${LOCAL_API_ORIGIN}/weekly-snippets`, {
    data: { content },
    headers: {
      'content-type': 'application/json',
      'x-csrf-token': csrfToken,
      'x-test-now': NOW,
    },
  });
  expect(res.ok()).toBeTruthy();
  const body = (await res.json()) as { id: number };
  return body.id;
}

test.describe('Search 기능 High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test('[CHK-SEARCH-001] @high 네비게이션 바에서 /search 페이지로 이동', async ({ page }) => {
    await setupApiProxy(page);

    await page.goto('/');
    await expect(page).toHaveURL('/');

    // 데스크탑 검색 아이콘 클릭
    const searchLink = page.locator('a[href="/search"][aria-label="검색"]').first();
    await expect(searchLink).toBeVisible();
    await searchLink.click();

    await expect(page).toHaveURL(/\/search/);
    await expect(page.getByRole('heading', { name: '스니펫 검색' })).toBeVisible();

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-002] @high /search 페이지 기본 UI 렌더링', async ({ page }) => {
    await setupApiProxy(page);

    await page.goto('/search');
    await expect(page).toHaveURL('/search');

    await expect(page.getByRole('heading', { name: '스니펫 검색' })).toBeVisible();

    // 검색 입력 필드
    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await expect(searchInput).toBeVisible();

    // type 탭
    await expect(page.getByRole('tab', { name: '전체' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '일간' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '주간' })).toBeVisible();

    // scope 토글 버튼
    await expect(page.getByRole('button', { name: '내 스니펫' })).toBeVisible();
    await expect(page.getByRole('button', { name: '팀 스니펫' })).toBeVisible();

    // 짧은 쿼리 안내 문구 (초기 상태)
    await expect(page.getByText('검색어를 2자 이상 입력하세요')).toBeVisible();

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-003] @high 검색어 입력 시 URL 쿼리 파라미터 동기화', async ({ page }) => {
    await setupApiProxy(page);

    await page.goto('/search');

    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await searchInput.fill('테스트키워드');

    // debounce 300ms + URL 반영
    await expect(page).toHaveURL(/q=%ED%85%8C%EC%8A%A4%ED%8A%B8%ED%82%A4%EC%9B%8C%EB%93%9C/, {
      timeout: 2000,
    });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-004] @high type 탭 전환 시 URL 쿼리 파라미터 반영', async ({ page }) => {
    await setupApiProxy(page);

    await page.goto('/search?q=hello');

    await page.getByRole('tab', { name: '일간' }).click();
    await expect(page).toHaveURL(/type=daily/);

    await page.getByRole('tab', { name: '주간' }).click();
    await expect(page).toHaveURL(/type=weekly/);

    await page.getByRole('tab', { name: '전체' }).click();
    // type=all 은 기본값이므로 URL에 type 파라미터가 없어야 함
    await expect(page).not.toHaveURL(/type=/);

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-005] @high scope 토글 전환 시 URL 쿼리 파라미터 반영', async ({ page }) => {
    await setupApiProxy(page);

    await page.goto('/search?q=hello');

    await page.getByRole('button', { name: '팀 스니펫' }).click();
    await expect(page).toHaveURL(/scope=team/);

    await page.getByRole('button', { name: '내 스니펫' }).click();
    // scope=own 은 기본값이므로 URL에 scope 파라미터 없어야 함
    await expect(page).not.toHaveURL(/scope=/);

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-006] @high 일간 스니펫 키워드 검색 후 결과 카드 표시', async ({ page }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH006-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    await createDailySnippet(page, `${uniqueKeyword} 일간 스니펫 내용입니다.`, csrfToken);

    await page.goto('/search');

    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await searchInput.fill(uniqueKeyword);

    // 결과 카드 대기
    const resultCard = page.locator('[role="button"]').filter({ hasText: uniqueKeyword }).first();
    await expect(resultCard).toBeVisible({ timeout: 10_000 });

    // 일간 배지 확인 (badge 엘리먼트 한정)
    await expect(resultCard.locator('[data-slot="badge"]').filter({ hasText: '일간' })).toBeVisible();

    // 키워드 하이라이트 mark 태그 확인
    const highlight = resultCard.locator('mark').filter({ hasText: uniqueKeyword });
    await expect(highlight).toBeVisible();

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-007] @high 주간 스니펫 키워드 검색 후 결과 카드 표시', async ({ page }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH007-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    await createWeeklySnippet(page, `${uniqueKeyword} 주간 스니펫 내용입니다.`, csrfToken);

    await page.goto('/search');

    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await searchInput.fill(uniqueKeyword);

    const resultCard = page.locator('[role="button"]').filter({ hasText: uniqueKeyword }).first();
    await expect(resultCard).toBeVisible({ timeout: 10_000 });

    // 주간 배지 확인 (badge 엘리먼트 한정)
    await expect(resultCard.locator('[data-slot="badge"]').filter({ hasText: '주간' })).toBeVisible();

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-008] @high type=daily 필터로 일간 결과만 표시', async ({ page }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH008-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    await createDailySnippet(page, `${uniqueKeyword} 일간 전용 내용`, csrfToken);
    await createWeeklySnippet(page, `${uniqueKeyword} 주간 전용 내용`, csrfToken);

    await page.goto(`/search?q=${encodeURIComponent(uniqueKeyword)}&type=daily`);

    // 일간 배지 결과는 있어야 함
    const dailyCards = page.locator('[role="button"]').filter({ has: page.locator('[data-slot="badge"]').filter({ hasText: '일간' }) });
    await expect(dailyCards.first()).toBeVisible({ timeout: 10_000 });

    // 주간 배지 결과는 없어야 함
    const weeklyCards = page.locator('[role="button"]').filter({ has: page.locator('[data-slot="badge"]').filter({ hasText: '주간' }) });
    await expect(weeklyCards).toHaveCount(0);

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-009] @high type=weekly 필터로 주간 결과만 표시', async ({ page }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH009-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    await createDailySnippet(page, `${uniqueKeyword} 일간 전용 내용`, csrfToken);
    await createWeeklySnippet(page, `${uniqueKeyword} 주간 전용 내용`, csrfToken);

    await page.goto(`/search?q=${encodeURIComponent(uniqueKeyword)}&type=weekly`);

    // 주간 결과는 있어야 함
    const weeklyCards = page.locator('[role="button"]').filter({ has: page.locator('[data-slot="badge"]').filter({ hasText: '주간' }) });
    await expect(weeklyCards.first()).toBeVisible({ timeout: 10_000 });

    // 일간 결과는 없어야 함
    const dailyCards = page.locator('[role="button"]').filter({ has: page.locator('[data-slot="badge"]').filter({ hasText: '일간' }) });
    await expect(dailyCards).toHaveCount(0);

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-010] @high 존재하지 않는 키워드 검색 시 빈 상태 표시', async ({ page }) => {
    await setupApiProxy(page);

    const noResultKeyword = `NORESULT-${Date.now()}-xyzzy`;
    await page.goto(`/search?q=${encodeURIComponent(noResultKeyword)}`);

    await expect(page.getByText('검색 결과가 없습니다')).toBeVisible({ timeout: 10_000 });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-011] @high 1자 이하 검색어 시 안내 문구 표시 (API 미호출)', async ({ page }) => {
    await setupApiProxy(page);

    let searchApiCalled = false;
    await page.route(`${LOCAL_API_ORIGIN}/daily-snippets*`, (route) => {
      if (route.request().url().includes('q=')) {
        searchApiCalled = true;
      }
      return route.continue();
    });

    await page.goto('/search');

    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await searchInput.fill('a');

    // debounce 대기
    await page.waitForTimeout(500);

    await expect(page.getByText('검색어를 2자 이상 입력하세요')).toBeVisible();
    expect(searchApiCalled).toBe(false);

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-012] @high 결과 카드 클릭 시 해당 스니펫 상세 페이지로 이동', async ({
    page,
  }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH012-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    const snippetId = await createDailySnippet(
      page,
      `${uniqueKeyword} 클릭 이동 테스트 내용`,
      csrfToken,
    );

    await page.goto(`/search?q=${encodeURIComponent(uniqueKeyword)}&type=daily`);

    const resultCard = page.locator('[role="button"]').filter({ hasText: uniqueKeyword }).first();
    await expect(resultCard).toBeVisible({ timeout: 10_000 });
    await resultCard.click();

    await expect(page).toHaveURL(new RegExp(`/daily-snippets.*id=${snippetId}`), {
      timeout: 5000,
    });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-SEARCH-013] @high URL 쿼리로 직접 접근 시 검색 즉시 실행', async ({ page }) => {
    await setupApiProxy(page);

    const uniqueKeyword = `SRCH013-${Date.now()}`;
    const csrfToken = await getCsrfToken(page);
    await createDailySnippet(page, `${uniqueKeyword} URL 직접 접근 테스트`, csrfToken);

    await page.goto(
      `/search?q=${encodeURIComponent(uniqueKeyword)}&type=daily&scope=own`,
    );

    // 입력창에 쿼리 값이 복원돼야 함
    const searchInput = page.getByPlaceholder(/검색어를 입력하세요/);
    await expect(searchInput).toHaveValue(uniqueKeyword);

    // 탭 상태 확인
    const dailyTab = page.getByRole('tab', { name: '일간' });
    await expect(dailyTab).toHaveAttribute('data-state', 'active');

    // 내 스니펫 버튼 활성 상태
    const ownButton = page.getByRole('button', { name: '내 스니펫' });
    await expect(ownButton).toBeVisible();

    // 결과 카드 표시
    const resultCard = page.locator('[role="button"]').filter({ hasText: uniqueKeyword }).first();
    await expect(resultCard).toBeVisible({ timeout: 10_000 });

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });
});
