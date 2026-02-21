type SnippetKind = 'daily' | 'weekly';

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

type PageDataResponse = {
  snippet?: Record<string, unknown> | null;
  read_only?: boolean;
  prev_id?: number | null;
  next_id?: number | null;
};

export async function loadSnippetPageData({ kind, idParam, client }: Params) {
  const endpoint = kind === 'daily' ? '/daily-snippets/page-data' : '/weekly-snippets/page-data';
  const query = idParam ? `?id=${encodeURIComponent(idParam)}` : '';

  const response = await client.get<PageDataResponse>(`${endpoint}${query}`);
  const snippet = response?.snippet ?? null;
  const snippetEditable = snippet?.editable;

  const readOnly =
    typeof response?.read_only === 'boolean'
      ? response.read_only
      : typeof snippetEditable === 'boolean'
        ? !snippetEditable
        : false;

  return {
    snippet,
    readOnly,
    prevId: typeof response?.prev_id === 'number' ? response.prev_id : null,
    nextId: typeof response?.next_id === 'number' ? response.next_id : null,
  };
}
