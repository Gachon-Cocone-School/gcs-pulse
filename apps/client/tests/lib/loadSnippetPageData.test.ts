import { describe, expect, it } from 'vitest';
import { loadSnippetPageData } from '../../src/lib/loadSnippetPageData';

type FakeResponse = Record<string, unknown>;

function createClient(responses: Record<string, FakeResponse>) {
  const calls: string[] = [];

  return {
    calls,
    async get(url: string): Promise<FakeResponse> {
      calls.push(url);
      const response = responses[url];
      if (!response) {
        throw new Error(`Unhandled URL: ${url}`);
      }
      return response;
    },
  };
}

describe('loadSnippetPageData', () => {
  it('loads daily snippet and adjacent ids', async () => {
    const client = createClient({
      '/snippet_date': { date: '2026-02-14' },
      '/daily-snippets?from_date=2026-02-14&to_date=2026-02-14&limit=1': {
        items: [{ id: 101, date: '2026-02-14', content: 'daily', editable: true }],
      },
      '/daily-snippets?to_date=2026-02-13&order=desc&limit=1': { items: [{ id: 100 }] },
      '/daily-snippets?from_date=2026-02-15&order=asc&limit=1': { items: [{ id: 102 }] },
    });

    const result = await loadSnippetPageData({
      kind: 'daily',
      idParam: null,
      fallbackKey: '2026-02-14',
      client,
      normalizeServerDate: (value) => value,
    });

    expect(result.snippet).toMatchObject({ id: 101, date: '2026-02-14' });
    expect(result.prevId).toBe(100);
    expect(result.nextId).toBe(102);
    expect(result.readOnly).toBe(false);
  });

  it('loads weekly snippet with normalized server week and adjacent ids', async () => {
    const client = createClient({
      '/snippet_date': { date: '2026-02-14' },
      '/weekly-snippets?from_week=2026-02-09&to_week=2026-02-09&limit=1': {
        items: [{ id: 201, week: '2026-02-09', content: 'weekly' }],
      },
      '/weekly-snippets?to_week=2026-02-02&order=desc&limit=1': { items: [{ id: 200 }] },
      '/weekly-snippets?from_week=2026-02-16&order=asc&limit=1': { items: [{ id: 202 }] },
    });

    const result = await loadSnippetPageData({
      kind: 'weekly',
      idParam: null,
      fallbackKey: '2026-02-10',
      client,
      normalizeServerDate: () => '2026-02-09',
    });

    expect(result.snippet).toMatchObject({ id: 201, week: '2026-02-09' });
    expect(result.prevId).toBe(200);
    expect(result.nextId).toBe(202);
    expect(result.readOnly).toBe(false);
  });

  it('uses id endpoint when idParam exists', async () => {
    const client = createClient({
      '/snippet_date': { date: '2026-02-14' },
      '/daily-snippets/555': { id: 555, date: '2026-02-14', content: 'by-id' },
      '/daily-snippets?to_date=2026-02-13&order=desc&limit=1': { items: [] },
      '/daily-snippets?from_date=2026-02-15&order=asc&limit=1': { items: [] },
    });

    const result = await loadSnippetPageData({
      kind: 'daily',
      idParam: '555',
      fallbackKey: '2026-02-14',
      client,
      normalizeServerDate: (value) => value,
    });

    expect(result.snippet).toMatchObject({ id: 555, content: 'by-id' });
    expect(client.calls).toContain('/daily-snippets/555');
  });

  it('sets readOnly true when editable is false', async () => {
    const client = createClient({
      '/snippet_date': { date: '2026-02-14' },
      '/daily-snippets?from_date=2026-02-14&to_date=2026-02-14&limit=1': {
        items: [{ id: 301, date: '2026-02-14', editable: false }],
      },
      '/daily-snippets?to_date=2026-02-13&order=desc&limit=1': { items: [] },
      '/daily-snippets?from_date=2026-02-15&order=asc&limit=1': { items: [] },
    });

    const result = await loadSnippetPageData({
      kind: 'daily',
      idParam: null,
      fallbackKey: '2026-02-14',
      client,
      normalizeServerDate: (value) => value,
    });

    expect(result.readOnly).toBe(true);
  });

  it('uses key comparison fallback when editable is missing', async () => {
    const client = createClient({
      '/snippet_date': { date: '2026-02-14' },
      '/daily-snippets?from_date=2026-02-14&to_date=2026-02-14&limit=1': {
        items: [{ id: 401, date: '2026-02-13', content: 'past' }],
      },
      '/daily-snippets?to_date=2026-02-12&order=desc&limit=1': { items: [] },
      '/daily-snippets?from_date=2026-02-14&order=asc&limit=1': { items: [] },
    });

    const result = await loadSnippetPageData({
      kind: 'daily',
      idParam: null,
      fallbackKey: '2026-02-14',
      client,
      normalizeServerDate: (value) => value,
    });

    expect(result.readOnly).toBe(true);
  });
});
