import { describe, it, expect, afterEach, vi } from 'vitest';
import { fetchWithRetry, ApiError } from '../../src/lib/api';

describe('fetchWithRetry', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('throws ApiError(status=0) when fetch rejects with network error', async () => {
    // Mock global.fetch to simulate network failure
    (global as any).fetch = vi.fn(() => Promise.reject(new TypeError('Failed to fetch')));

    await expect(fetchWithRetry('http://localhost/api/test', { method: 'GET' })).rejects.toMatchObject({ status: 0 });
  });
});
