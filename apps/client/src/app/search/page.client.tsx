'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Search, Loader2, SearchX, SearchSlash } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { SearchResultCard } from '@/components/views/SearchResultCard';
import { Navigation } from '@/components/Navigation';

type SnippetKind = 'daily' | 'weekly';
type SearchType = 'all' | 'daily' | 'weekly';
type SearchScope = 'own' | 'team';

const LIMIT = 20;

interface SearchResult {
  id: number;
  kind: SnippetKind;
  date?: string;
  week?: string;
  [key: string]: unknown;
}

interface SearchPageClientProps {
  qParam?: string;
  typeParam?: string;
  scopeParam?: string;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

async function fetchSnippets(
  kind: SnippetKind,
  q: string,
  scope: SearchScope,
  offset: number,
): Promise<{ items: SearchResult[]; total: number }> {
  const params = new URLSearchParams({
    q,
    scope,
    limit: String(LIMIT),
    offset: String(offset),
  });
  const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
  const res = await api.get<{ items: any[]; total: number }>(`${endpoint}?${params}`);
  return {
    items: (res.items ?? []).map((item: any) => ({ ...item, kind })),
    total: res.total ?? 0,
  };
}

function mergeAndSort(daily: SearchResult[], weekly: SearchResult[]): SearchResult[] {
  const combined = [...daily, ...weekly];
  combined.sort((a, b) => {
    const aKey = (a.date ?? a.week ?? '') as string;
    const bKey = (b.date ?? b.week ?? '') as string;
    return bKey.localeCompare(aKey);
  });
  return combined;
}

export default function SearchPageClient({
  qParam = '',
  typeParam = 'all',
  scopeParam = 'own',
}: SearchPageClientProps) {
  const router = useRouter();

  const validType = (['all', 'daily', 'weekly'] as SearchType[]).includes(typeParam as SearchType)
    ? (typeParam as SearchType)
    : 'all';
  const validScope = (['own', 'team'] as SearchScope[]).includes(scopeParam as SearchScope)
    ? (scopeParam as SearchScope)
    : 'own';

  const [inputValue, setInputValue] = React.useState(qParam);
  const [searchType, setSearchType] = React.useState<SearchType>(validType);
  const [searchScope, setSearchScope] = React.useState<SearchScope>(validScope);

  // Accumulated results
  const [items, setItems] = React.useState<SearchResult[]>([]);
  const [hasMore, setHasMore] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Offset refs per kind for type=all paging
  const dailyOffsetRef = React.useRef(0);
  const weeklyOffsetRef = React.useRef(0);
  const singleOffsetRef = React.useRef(0);

  const debouncedQuery = useDebounce(inputValue, 300);

  // Sync URL when filters change
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedQuery) params.set('q', debouncedQuery);
    if (searchType !== 'all') params.set('type', searchType);
    if (searchScope !== 'own') params.set('scope', searchScope);
    const query = params.toString();
    router.replace(`/search${query ? `?${query}` : ''}`, { scroll: false });
  }, [debouncedQuery, searchType, searchScope, router]);

  // Initial search when filters change
  const doInitialSearch = React.useCallback(
    async (q: string, type: SearchType, scope: SearchScope) => {
      if (q.trim().length < 2) {
        setItems([]);
        setHasMore(false);
        return;
      }

      setLoading(true);
      setError(null);
      dailyOffsetRef.current = 0;
      weeklyOffsetRef.current = 0;
      singleOffsetRef.current = 0;

      try {
        if (type === 'all') {
          const [dailyRes, weeklyRes] = await Promise.all([
            fetchSnippets('daily', q, scope, 0),
            fetchSnippets('weekly', q, scope, 0),
          ]);
          dailyOffsetRef.current = dailyRes.items.length;
          weeklyOffsetRef.current = weeklyRes.items.length;
          const merged = mergeAndSort(dailyRes.items, weeklyRes.items);
          setItems(merged);
          setHasMore(
            dailyOffsetRef.current < dailyRes.total ||
              weeklyOffsetRef.current < weeklyRes.total,
          );
        } else {
          const res = await fetchSnippets(type as SnippetKind, q, scope, 0);
          singleOffsetRef.current = res.items.length;
          setItems(res.items);
          setHasMore(res.items.length < res.total);
        }
      } catch (err) {
        console.error('Search failed', err);
        setError('검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        setItems([]);
        setHasMore(false);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Load more (infinite scroll)
  const loadMore = React.useCallback(async () => {
    if (loadingMore || !hasMore || debouncedQuery.trim().length < 2) return;

    setLoadingMore(true);
    try {
      if (searchType === 'all') {
        const [dailyRes, weeklyRes] = await Promise.all([
          fetchSnippets('daily', debouncedQuery, searchScope, dailyOffsetRef.current),
          fetchSnippets('weekly', debouncedQuery, searchScope, weeklyOffsetRef.current),
        ]);
        dailyOffsetRef.current += dailyRes.items.length;
        weeklyOffsetRef.current += weeklyRes.items.length;
        const merged = mergeAndSort(dailyRes.items, weeklyRes.items);
        setItems((prev) => [...prev, ...merged]);
        setHasMore(
          dailyOffsetRef.current < dailyRes.total ||
            weeklyOffsetRef.current < weeklyRes.total,
        );
      } else {
        const res = await fetchSnippets(
          searchType as SnippetKind,
          debouncedQuery,
          searchScope,
          singleOffsetRef.current,
        );
        singleOffsetRef.current += res.items.length;
        setItems((prev) => [...prev, ...res.items]);
        setHasMore(singleOffsetRef.current < res.total);
      }
    } catch (err) {
      console.error('Load more failed', err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, debouncedQuery, searchType, searchScope]);

  // Trigger search when debounced query / type / scope change
  React.useEffect(() => {
    void doInitialSearch(debouncedQuery, searchType, searchScope);
  }, [debouncedQuery, searchType, searchScope, doInitialSearch]);

  // IntersectionObserver for infinite scroll
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore && !loadingMore) {
          void loadMore();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, loadMore]);

  const handleTypeChange = (val: string) => {
    setSearchType(val as SearchType);
  };

  const handleScopeToggle = (scope: SearchScope) => {
    setSearchScope(scope);
  };

  const showEmptyState = !loading && debouncedQuery.trim().length >= 2 && items.length === 0;
  const showPrompt = debouncedQuery.trim().length < 2;

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">스니펫 검색</h1>
        <p className="text-sm text-muted-foreground">키워드로 스니펫을 검색합니다.</p>
      </div>

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          type="search"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="검색어를 입력하세요 (최소 2자)"
          className="pl-9 h-11 text-base"
          suppressHydrationWarning
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Tabs value={searchType} onValueChange={handleTypeChange}>
          <TabsList>
            <TabsTrigger value="all">전체</TabsTrigger>
            <TabsTrigger value="daily">일간</TabsTrigger>
            <TabsTrigger value="weekly">주간</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex items-center rounded-lg border border-border p-1 gap-1">
          <Button
            variant={searchScope === 'own' ? 'default' : 'ghost'}
            size="sm"
            className="h-7 px-3 text-xs"
            onClick={() => handleScopeToggle('own')}
          >
            내 스니펫
          </Button>
          <Button
            variant={searchScope === 'team' ? 'default' : 'ghost'}
            size="sm"
            className="h-7 px-3 text-xs"
            onClick={() => handleScopeToggle('team')}
          >
            팀 스니펫
          </Button>
        </div>
      </div>

      {/* Results area */}
      <div className="space-y-4">
        {/* Initial loading */}
        {loading && (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        )}

        {/* Prompt to type */}
        {!loading && showPrompt && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <SearchSlash className="w-12 h-12 mb-4 opacity-20" />
            <p className="text-sm">검색어를 2자 이상 입력하세요.</p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center py-20 text-destructive">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Empty state */}
        {!loading && showEmptyState && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground bg-card rounded-xl border border-dashed border-border">
            <SearchX className="w-12 h-12 mb-4 opacity-20" />
            <p className="text-sm font-medium">검색 결과가 없습니다.</p>
            <p className="text-xs mt-1 opacity-60">다른 키워드로 검색해보세요.</p>
          </div>
        )}

        {/* Result count */}
        {!loading && items.length > 0 && (
          <p className="text-xs text-muted-foreground">
            {items.length}개 결과
            {hasMore ? ' (더 있음)' : ''}
          </p>
        )}

        {/* Result cards */}
        {!loading && (
          <div className={cn('space-y-4', items.length === 0 && 'hidden')}>
            {items.map((snippet) => (
              <SearchResultCard
                key={`${snippet.kind}-${snippet.id}`}
                snippet={snippet}
                kind={snippet.kind}
                keyword={debouncedQuery}
              />
            ))}
          </div>
        )}

        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} className="h-1" />

        {/* Load more spinner */}
        {loadingMore && (
          <div className="flex justify-center py-6">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        )}
      </div>
    </div>
    </div>
  );
}
