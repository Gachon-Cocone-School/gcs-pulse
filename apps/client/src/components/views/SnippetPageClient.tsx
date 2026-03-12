'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { hasPrivilegedRole } from '@/lib/types';
import SnippetForm from '@/components/views/SnippetForm';
import { Navigation } from '@/components/Navigation';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/PageHeader';
import { Loader2, ArrowLeft, ArrowRight, User, Users } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { loadSnippetPageData } from '@/lib/loadSnippetPageData';
import { useSnippetStreamingActions } from '@/components/views/useSnippetStreamingActions';
import { getWeekStartDateKey } from '@/lib/dateKeys';
import { Input } from '@/components/ui/input';

const TeamSnippetFeed = dynamic(
  () => import('@/components/views/TeamSnippetFeed').then((mod) => mod.TeamSnippetFeed),
  {
    loading: () => (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    ),
  },
);

type SnippetKind = 'daily' | 'weekly';

interface SnippetPageClientProps {
  kind: SnippetKind;
  idParam?: string;
  viewParam?: string;
  highlightCommentIdParam?: string;
  testNowParam?: string;
  fallbackKey: string;
  keyParam?: string;
}

const PAGE_TEXT = {
  daily: {
    titleLabel: '일간',
    descriptionWhenLoaded: '매일의 작은 기록을 남겨보세요.',
    descriptionWhenEmpty: '오늘의 작은 기록을 남겨보세요.',
    prevTitle: '이전 스니펫',
    nextTitle: '다음 스니펫',
  },
  weekly: {
    titleLabel: '주간',
    descriptionWhenLoaded: '매주의 핵심을 정리해보세요.',
    descriptionWhenEmpty: '금주의 핵심을 정리해보세요.',
    prevTitle: '이전 주',
    nextTitle: '다음 주',
  },
} as const;

const KEY_FIELD = {
  daily: 'date',
  weekly: 'week',
} as const;

export function SnippetPageClient({
  kind,
  idParam,
  viewParam,
  highlightCommentIdParam,
  testNowParam,
  fallbackKey,
  keyParam,
}: SnippetPageClientProps) {
  const router = useRouter();
  const activeView = kind === 'weekly' ? (viewParam === 'team' ? 'team' : 'my') : (viewParam ?? 'my');

  const { user, isAuthenticated, isLoading } = useAuth();
  const [snippet, setSnippet] = React.useState<any>(null);
  const hasAccess = hasPrivilegedRole(user?.roles);
  const [loading, setLoading] = React.useState(true);
  const [organizing, setOrganizing] = React.useState(false);
  const [generatingFeedback, setGeneratingFeedback] = React.useState(false);
  const [readOnly, setReadOnly] = React.useState(false);
  const [prevId, setPrevId] = React.useState<number | null>(null);
  const [nextId, setNextId] = React.useState<number | null>(null);

  const pageText = PAGE_TEXT[kind];
  const keyField = KEY_FIELD[kind];
  const keyParamName = kind === 'daily' ? 'date' : 'week';
  const basePath = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
  const highlightCommentId =
    highlightCommentIdParam && Number.isFinite(Number(highlightCommentIdParam))
      ? Number(highlightCommentIdParam)
      : undefined;

  const requestHeaders = React.useMemo<Record<string, string> | undefined>(() => {
    return testNowParam ? { 'x-test-now': testNowParam } : undefined;
  }, [testNowParam]);

  const normalizeKeyInput = React.useCallback(
    (value: string) => {
      const normalizedValue =
        kind === 'weekly' ? getWeekStartDateKey(new Date(`${value}T12:00:00`)) : value;

      return normalizedValue > fallbackKey ? fallbackKey : normalizedValue;
    },
    [kind, fallbackKey],
  );

  const normalizedKeyParam = React.useMemo(() => {
    if (!keyParam) return null;
    return normalizeKeyInput(keyParam);
  }, [keyParam, normalizeKeyInput]);

  const loadSnippet = React.useCallback(async (silent = false) => {
    if (!silent) setLoading(true);

    try {
      const result = await loadSnippetPageData({
        kind,
        idParam: idParam ?? null,
        keyParam: normalizedKeyParam,
        client: {
          get: (url) => api.get(url, { headers: requestHeaders }),
        },
      });

      setSnippet(result.snippet);
      setReadOnly(result.readOnly);
      setPrevId(result.prevId);
      setNextId(result.nextId);
    } catch (err) {
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [kind, idParam, normalizedKeyParam, requestHeaders]);

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (isAuthenticated && hasAccess) {
      loadSnippet();
    }
  }, [isLoading, isAuthenticated, hasAccess, router, loadSnippet]);

  const handleSave = async (content: string) => {
    if (snippet?.id) {
      await api.put(`${basePath}/${snippet.id}`, { content }, { headers: requestHeaders });
    } else {
      await api.post(basePath, { content }, { headers: requestHeaders });
    }
    await loadSnippet(true);
  };

  const { handleOrganize, handleGenerateFeedback } = useSnippetStreamingActions({
    kind,
    basePath,
    requestHeaders,
    setSnippet,
    setOrganizing,
    setGeneratingFeedback,
  });

  function pushWithPreservedQuery(overrides: Record<string, string | number | null>) {
    const params = new URLSearchParams(window.location.search);
    Object.entries(overrides).forEach(([k, v]) => {
      if (v == null) params.delete(k);
      else params.set(k, String(v));
    });
    router.push(`${basePath}?${params.toString()}`);
  }

  const goToSnippet = (id: number) => {
    pushWithPreservedQuery({ id, [keyParamName]: null, highlight_comment_id: null });
  };

  const snippetKey = typeof snippet?.[keyField] === 'string' ? snippet[keyField] : null;
  const selectedKey = normalizedKeyParam ?? snippetKey ?? fallbackKey;
  const canGoBackToCurrent =
    kind === 'daily' && snippetKey !== null && snippetKey < fallbackKey;

  const handleSelectKey = (value: string) => {
    if (!value) return;

    const normalizedValue = normalizeKeyInput(value);

    pushWithPreservedQuery({
      id: null,
      [keyParamName]: normalizedValue,
      highlight_comment_id: null,
    });
  };

  const handleGoToNextSnippet = () => {
    if (nextId) {
      goToSnippet(nextId);
      return;
    }

    if (canGoBackToCurrent) {
      pushWithPreservedQuery({ id: null, [keyParamName]: null });
    }
  };

  if (!hasAccess) {
    return <AccessDeniedView reason="student-only" />;
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title={`${pageText.titleLabel} : ${selectedKey}`}
          description={snippet ? pageText.descriptionWhenLoaded : pageText.descriptionWhenEmpty}
          actions={
            <>
              <Input
                type="date"
                className="w-[160px]"
                value={selectedKey}
                onChange={(e) => handleSelectKey(e.target.value)}
                aria-label={kind === 'daily' ? '일간 조회 날짜 선택' : '주간 조회 날짜 선택'}
              />
              <Button
                variant="outline"
                size="icon"
                disabled={!prevId}
                onClick={() => prevId && goToSnippet(prevId)}
                title={pageText.prevTitle}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                disabled={!nextId && !canGoBackToCurrent}
                onClick={handleGoToNextSnippet}
                title={pageText.nextTitle}
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          }
        />

        <Tabs
          value={activeView}
          onValueChange={(v) => pushWithPreservedQuery({ view: v, highlight_comment_id: null })}
          className="w-full"
        >
          <TabsList className="mb-6">
            <TabsTrigger value="my" className="gap-2 data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]">
              <User className="h-4 w-4" />
              나의 기록
            </TabsTrigger>
            <TabsTrigger value="team" className="gap-2 data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] data-[state=active]:border-[var(--sys-current-border)]">
              <Users className="h-4 w-4" />
              팀 피드
            </TabsTrigger>
          </TabsList>

          <TabsContent value="my" className="mt-0">
            <div className="w-full glass-card border-[var(--sys-current-border)] p-6 rounded-xl animate-entrance">
              <SnippetForm
                initialContent={snippet?.content || ''}
                onSave={handleSave}
                readOnly={readOnly}
                onOrganize={handleOrganize}
                onGenerateFeedback={handleGenerateFeedback}
                isOrganizing={organizing}
                isGeneratingFeedback={generatingFeedback}
                feedback={snippet?.feedback}
              />
            </div>
          </TabsContent>

          <TabsContent value="team" className="mt-0">
            <TeamSnippetFeed kind={kind} id={idParam} highlightCommentId={highlightCommentId} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
