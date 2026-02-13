import { describe, expect, it } from 'vitest';
import { addDaysToDateKey, getWeekStartDateKey, toDateKey } from '../../src/lib/dateKeys';

describe('date key utils', () => {
  it('formats a date to YYYY-MM-DD', () => {
    expect(toDateKey(new Date('2026-02-14T10:20:30.000Z'))).toBe('2026-02-14');
  });

  it('returns monday as week start key', () => {
    expect(getWeekStartDateKey(new Date('2026-02-11T10:00:00.000Z'))).toBe('2026-02-09');
    expect(getWeekStartDateKey(new Date('2026-02-09T10:00:00.000Z'))).toBe('2026-02-09');
    expect(getWeekStartDateKey(new Date('2026-02-15T10:00:00.000Z'))).toBe('2026-02-09');
  });

  it('moves date key by day offsets', () => {
    expect(addDaysToDateKey('2026-02-14', -1)).toBe('2026-02-13');
    expect(addDaysToDateKey('2026-02-14', 1)).toBe('2026-02-15');
    expect(addDaysToDateKey('2026-02-14', 7)).toBe('2026-02-21');
  });
});
