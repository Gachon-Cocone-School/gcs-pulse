import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test, expect, type Page } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000';
const REMOTE_API_ORIGIN = process.env.E2E_REMOTE_API_ORIGIN || 'http://localhost:8000';
const CLIENT_API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || REMOTE_API_ORIGIN;
const API_PROXY_ORIGINS = Array.from(new Set([REMOTE_API_ORIGIN, CLIENT_API_ORIGIN]));
const SERVER_ROOT = resolve(process.cwd(), '../server');

const PROFESSOR_EMAIL = 'e2e-meeting-prof@gachon.ac.kr';
const PROFESSOR_NAME = 'E2E Meeting Professor';
const GCS_EMAIL = 'e2e-meeting-gcs@gachon.ac.kr';
const GCS_NAME = 'E2E Meeting GCS';
const FORBIDDEN_EMAIL = 'e2e-meeting-forbidden@gachon.ac.kr';
const FORBIDDEN_NAME = 'E2E Meeting Forbidden';

let cachedProfessorSessionCookie: string | null = null;
let cachedGcsSessionCookie: string | null = null;
let cachedForbiddenSessionCookie: string | null = null;

type SessionBootstrapResult = {
  session_cookie: string;
};

type MeetingFixtures = {
  room_id: number;
  owner_user_id: number;
};

function toLocalApiUrl(url: string): string {
  if (url.startsWith(REMOTE_API_ORIGIN)) {
    return url.replace(REMOTE_API_ORIGIN, API_BASE);
  }
  return url;
}

function resolveServerPythonExecutable(): string {
  if (process.env.E2E_SERVER_PYTHON) {
    return process.env.E2E_SERVER_PYTHON;
  }

  const venvPython = resolve(SERVER_ROOT, 'venv/bin/python');
  if (existsSync(venvPython)) {
    return venvPython;
  }

  return 'python3';
}

function runServerPython<T>(script: string, env: Record<string, string>): T {
  const pythonExecutable = resolveServerPythonExecutable();
  const result = spawnSync(pythonExecutable, ['-c', script], {
    cwd: SERVER_ROOT,
    encoding: 'utf-8',
    env: {
      ...process.env,
      PYTHONPATH: SERVER_ROOT,
      ...env,
    },
  });

  if (result.error) {
    throw new Error(`Failed to run server python script: ${result.error.message}`);
  }

  if (result.status !== 0) {
    throw new Error(
      `Server python script failed (exit ${result.status}): ${(result.stderr || result.stdout || '').trim()}`,
    );
  }

  const output = result.stdout
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .at(-1);

  if (!output) {
    throw new Error('Server python script returned empty output');
  }

  return JSON.parse(output) as T;
}

function bootstrapSessionCookie(email: string, name: string, roles: string[]): string {
  const script = [
    'import asyncio',
    'import base64',
    'import json',
    'import os',
    'from sqlalchemy import select',
    'from itsdangerous import TimestampSigner',
    'from app import crud',
    'from app.core.config import settings',
    'from app.database import AsyncSessionLocal',
    'from app.models import User',
    '',
    'EMAIL = os.environ["E2E_SESSION_EMAIL"]',
    'NAME = os.environ["E2E_SESSION_NAME"]',
    'ROLES = [role.strip() for role in os.environ.get("E2E_SESSION_ROLES", "gcs").split(",") if role.strip()]',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": EMAIL,',
    '                "name": NAME,',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '        user_result = await db.execute(select(User).filter(User.email == EMAIL))',
    '        user = user_result.scalars().first()',
    '        if user is None:',
    '            raise RuntimeError("Failed to resolve user")',
    '        user.roles = ROLES',
    '        await db.commit()',
    '',
    '    payload = {',
    '        "user": {',
    '            "email": EMAIL,',
    '            "name": NAME,',
    '            "picture": "",',
    '            "email_verified": True,',
    '        }',
    '    }',
    '    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))',
    '    cookie = TimestampSigner(str(settings.SECRET_KEY)).sign(encoded).decode("utf-8")',
    '    print(json.dumps({"session_cookie": cookie}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  const result = runServerPython<SessionBootstrapResult>(script, {
    E2E_SESSION_EMAIL: email,
    E2E_SESSION_NAME: name,
    E2E_SESSION_ROLES: roles.join(','),
  });

  if (!result.session_cookie) {
    throw new Error('Session bootstrap did not return session_cookie');
  }

  return result.session_cookie;
}

function ensureProfessorSessionCookie(): string {
  if (!cachedProfessorSessionCookie) {
    cachedProfessorSessionCookie = bootstrapSessionCookie(PROFESSOR_EMAIL, PROFESSOR_NAME, ['admin']);
  }
  return cachedProfessorSessionCookie;
}

function ensureGcsSessionCookie(): string {
  if (!cachedGcsSessionCookie) {
    cachedGcsSessionCookie = bootstrapSessionCookie(GCS_EMAIL, GCS_NAME, ['gcs']);
  }
  return cachedGcsSessionCookie;
}

function ensureForbiddenSessionCookie(): string {
  if (!cachedForbiddenSessionCookie) {
    cachedForbiddenSessionCookie = bootstrapSessionCookie(FORBIDDEN_EMAIL, FORBIDDEN_NAME, ['가천대학교']);
  }
  return cachedForbiddenSessionCookie;
}

function ensureMeetingFixtures(): MeetingFixtures {
  const script = [
    'import asyncio',
    'import json',
    'import os',
    'from datetime import datetime, timezone',
    'from sqlalchemy import delete, select',
    'from app import crud',
    'from app.database import AsyncSessionLocal',
    'from app.models import MeetingRoom, MeetingRoomReservation, User',
    '',
    'OWNER_EMAIL = os.environ["E2E_MEETING_OWNER_EMAIL"]',
    'OWNER_NAME = os.environ["E2E_MEETING_OWNER_NAME"]',
    '',
    'async def main() -> None:',
    '    async with AsyncSessionLocal() as db:',
    '        await crud.create_or_update_user(',
    '            db,',
    '            {',
    '                "email": OWNER_EMAIL,',
    '                "name": OWNER_NAME,',
    '                "picture": "",',
    '                "email_verified": True,',
    '            },',
    '        )',
    '',
    '        owner_result = await db.execute(select(User).filter(User.email == OWNER_EMAIL))',
    '        owner = owner_result.scalars().first()',
    '        if owner is None:',
    '            raise RuntimeError("Failed to resolve meeting owner")',
    '        owner.roles = ["gcs"]',
    '',
    '        room_result = await db.execute(select(MeetingRoom).order_by(MeetingRoom.id.asc()))',
    '        room = room_result.scalars().first()',
    '        if room is None:',
    '            room = MeetingRoom(name="E2E 회의실", location="본관", description="E2E", image_url=None)',
    '            db.add(room)',
    '            await db.flush()',
    '',
    '        await db.execute(delete(MeetingRoomReservation).where(MeetingRoomReservation.meeting_room_id == room.id))',
    '',
    '        seed = MeetingRoomReservation(',
    '            meeting_room_id=room.id,',
    '            reserved_by_user_id=owner.id,',
    '            start_at=datetime(2026, 3, 13, 18, 0, tzinfo=timezone.utc),',
    '            end_at=datetime(2026, 3, 13, 19, 0, tzinfo=timezone.utc),',
    '            purpose="E2E seed reservation",',
    '        )',
    '        db.add(seed)',
    '',
    '        await db.commit()',
    '        print(json.dumps({"room_id": room.id, "owner_user_id": owner.id}))',
    '',
    'asyncio.run(main())',
  ].join('\n');

  return runServerPython<MeetingFixtures>(script, {
    E2E_MEETING_OWNER_EMAIL: GCS_EMAIL,
    E2E_MEETING_OWNER_NAME: GCS_NAME,
  });
}

async function setSessionCookieForApi(page: Page, sessionCookie: string): Promise<void> {
  const apiUrl = new URL(API_BASE);
  const hosts = apiUrl.hostname === 'localhost' ? ['localhost', '127.0.0.1'] : [apiUrl.hostname];

  await page.context().addCookies(
    hosts.map((host) => ({
      name: 'session',
      value: sessionCookie,
      domain: host,
      path: '/',
      httpOnly: true,
      secure: apiUrl.protocol === 'https:',
      sameSite: 'Lax' as const,
      expires: Math.floor(Date.now() / 1000) + 14 * 24 * 60 * 60,
    })),
  );
}

async function setupApiProxy(page: Page): Promise<void> {
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
}

async function selectTimePart(page: Page, triggerTestId: string, value: string): Promise<void> {
  await page.getByTestId(triggerTestId).click();
  const openedPicker = page.locator('div.h-40.overflow-y-auto').last();
  await openedPicker.getByRole('button', { name: value, exact: true }).click();
}

async function selectReservationTime(
  page: Page,
  time: { startHour: string; startMinute: string; endHour: string; endMinute: string },
): Promise<void> {
  await selectTimePart(page, 'meeting-room-start-hour-trigger', time.startHour);
  await selectTimePart(page, 'meeting-room-start-minute-trigger', time.startMinute);
  await selectTimePart(page, 'meeting-room-end-hour-trigger', time.endHour);
  await selectTimePart(page, 'meeting-room-end-minute-trigger', time.endMinute);
}

test.describe('Meeting rooms High checklist', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(() => {
    ensureMeetingFixtures();
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('[CHK-MEETING-001] @high 비권한 사용자는 접근 거부 화면', async ({ page }) => {
    await setSessionCookieForApi(page, ensureForbiddenSessionCookie());
    await setupApiProxy(page);

    await page.goto('/meeting-rooms');

    await expect(page.getByText('접근 권한이 없습니다')).toBeVisible();
  });

  test('[CHK-MEETING-002] @high 권한 사용자는 목록/예약폼/예약테이블 확인', async ({ page }) => {
    await setSessionCookieForApi(page, ensureGcsSessionCookie());
    await setupApiProxy(page);

    await page.goto('/meeting-rooms?date=2026-03-13');

    await expect(page.getByTestId('meeting-room-create-form')).toBeVisible();
    await expect(page.getByTestId('meeting-room-reservations-table')).toBeVisible();
    await expect(page.getByTestId('meeting-room-date-input')).toHaveValue('2026-03-13');

    await expect(page.getByTestId('meeting-room-select')).toBeVisible();
  });

  test('[CHK-MEETING-003] @high 예약 생성 후 예약 행 반영', async ({ page }) => {
    await setSessionCookieForApi(page, ensureGcsSessionCookie());
    await setupApiProxy(page);

    const uniquePurpose = `E2E reservation ${Date.now()}`;

    await page.goto('/meeting-rooms?date=2026-03-13');

    await selectReservationTime(page, {
      startHour: '13',
      startMinute: '00',
      endHour: '14',
      endMinute: '00',
    });
    await page.getByTestId('meeting-room-purpose-input').fill(uniquePurpose);

    await page.getByTestId('meeting-room-create-submit').click();

    const targetRow = page.locator('[data-testid^="meeting-room-reservation-row-"]', {
      hasText: uniquePurpose,
    });
    await expect(targetRow.first()).toBeVisible({ timeout: 10000 });
  });

  test('[CHK-MEETING-004] @high 중복 예약 생성 시 오류 토스트 노출', async ({ page }) => {
    await setSessionCookieForApi(page, ensureGcsSessionCookie());
    await setupApiProxy(page);

    await page.goto('/meeting-rooms?date=2026-03-13');

    await selectReservationTime(page, {
      startHour: '18',
      startMinute: '30',
      endHour: '18',
      endMinute: '45',
    });
    await page.getByTestId('meeting-room-purpose-input').fill('중복 예약 시도');

    await page.getByTestId('meeting-room-create-submit').click();

    await expect(page.getByText('선택한 시간대에 이미 예약이 있습니다. 다른 시간을 선택해 주세요.')).toBeVisible();
  });

  test('[CHK-MEETING-005] @high 본인 예약 취소 가능', async ({ page }) => {
    await setSessionCookieForApi(page, ensureGcsSessionCookie());
    await setupApiProxy(page);

    const uniquePurpose = `E2E cancel ${Date.now()}`;

    await page.goto('/meeting-rooms?date=2026-03-13');

    await selectReservationTime(page, {
      startHour: '15',
      startMinute: '00',
      endHour: '16',
      endMinute: '00',
    });
    await page.getByTestId('meeting-room-purpose-input').fill(uniquePurpose);
    await page.getByTestId('meeting-room-create-submit').click();

    const targetRow = page
      .locator('[data-testid^="meeting-room-reservation-row-"]', { hasText: uniquePurpose })
      .first();
    await expect(targetRow).toBeVisible({ timeout: 10000 });

    await targetRow.getByRole('button', { name: '취소' }).click();
    await expect(targetRow).toHaveCount(0);
  });

  test('[CHK-MEETING-006] @high admin은 타인 예약 취소 가능', async ({ page }) => {
    await setSessionCookieForApi(page, ensureProfessorSessionCookie());
    await setupApiProxy(page);

    await page.goto('/meeting-rooms?date=2026-03-13');

    const seedRow = page
      .locator('[data-testid^="meeting-room-reservation-row-"]', { hasText: 'E2E seed reservation' })
      .first();

    await expect(seedRow).toBeVisible({ timeout: 10000 });
    await seedRow.getByRole('button', { name: '취소' }).click();
    await expect(seedRow).toHaveCount(0);
  });
});
