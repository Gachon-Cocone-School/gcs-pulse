import { addDaysToDateKey } from './dateKeys';

export type SnippetKind = 'daily' | 'weekly';

type ApiClient = {
  get<T = unknown>(url: string): Promise<T>;
};

type Params = {
  kind: SnippetKind;
  idParam: string | null;
  fallbackKey: string;
  client: ApiClient;
  normalizeServerDate: (serverDate: string) => string;
};

type ItemResponse = {
  items?: Array<Record<string, unknown>>;
};

export async function loadSnippetPageData({ kind, idParam, fallbackKey, client, normalizeServerDate }: Params) {
  const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
  const keyName = kind === 'daily' ? 'date' : 'week';
  const fromKey = kind === 'daily' ? 'from_date' : 'from_week';
  const toKey = kind === 'daily' ? 'to_date' : 'to_week';

  let currentSnippet: Record<string, unknown> | null = null;
  let currentKey = fallbackKey;
  let serverKey = fallbackKey;

  const datePromise = client.get<{ date: string }>('/snippet_date').catch(() => null);

  if (idParam) {
    const [dateRes, snippetRes] = await Promise.all([
      datePromise,
      client.get<Record<string, unknown>>(`${endpoint}/${idParam}`).catch(() => null),
    ]);

    if (dateRes?.date) {
      serverKey = normalizeServerDate(dateRes.date);
    }

    currentSnippet = snippetRes;
  } else {
    const dateRes = await datePromise;
    if (dateRes?.date) {
      serverKey = normalizeServerDate(dateRes.date);
    }

    const listRes = await client
      .get<ItemResponse>(`${endpoint}?${fromKey}=${serverKey}&${toKey}=${serverKey}&limit=1`)
      .catch(() => null);
    currentSnippet = listRes?.items?.[0] ?? null;
  }

  const snippetKey = currentSnippet?.[keyName];
  if (typeof snippetKey === 'string') {
    currentKey = snippetKey;
  }

  const serverEditable = currentSnippet?.editable;
  const readOnly = typeof serverEditable === 'boolean' ? !serverEditable : currentKey < serverKey;

  const prevKey = addDaysToDateKey(currentKey, kind === 'daily' ? -1 : -7);
  const nextKey = addDaysToDateKey(currentKey, kind === 'daily' ? 1 : 7);

  const [prevRes, nextRes] = await Promise.all([
    client.get<ItemResponse>(`${endpoint}?${toKey}=${prevKey}&order=desc&limit=1`),
    client.get<ItemResponse>(`${endpoint}?${fromKey}=${nextKey}&order=asc&limit=1`),
  ]);

  return {
    snippet: currentSnippet,
    readOnly,
    prevId: typeof prevRes?.items?.[0]?.id === 'number' ? (prevRes.items[0].id as number) : null,
    nextId: typeof nextRes?.items?.[0]?.id === 'number' ? (nextRes.items[0].id as number) : null,
  };
}
