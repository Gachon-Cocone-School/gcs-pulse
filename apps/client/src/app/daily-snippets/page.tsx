'use client';

import React, { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import SnippetForm from '@/components/views/SnippetForm';
import { Navigation } from '@/components/Navigation';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/PageHeader';
import { Loader2, ArrowLeft, ArrowRight, User, Users } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TeamSnippetFeed } from '@/components/views/TeamSnippetFeed';
import { toDateKey } from '@/lib/dateKeys';
import { loadSnippetPageData } from '@/lib/loadSnippetPageData';

function DailySnippetsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get('id');
  const viewParam = searchParams.get('view') ?? 'my';

  const { isAuthenticated, isLoading } = useAuth();
  const [snippet, setSnippet] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [organizing, setOrganizing] = React.useState(false);
  const [readOnly, setReadOnly] = React.useState(false);
  const [prevId, setPrevId] = React.useState<number | null>(null);
  const [nextId, setNextId] = React.useState<number | null>(null);

  const today = toDateKey(new Date());

  const loadSnippet = React.useCallback(async (silent = false) => {
    if (!silent) setLoading(true);

    try {
      const result = await loadSnippetPageData({
        kind: 'daily',
        idParam,
        fallbackKey: today,
        client: api,
        normalizeServerDate: (value) => value,
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
  }, [today, idParam]);

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (isAuthenticated) {
      loadSnippet();
    }
  }, [isLoading, isAuthenticated, router, loadSnippet]);

  const handleSave = async (content: string) => {
    if (snippet?.id) {
      await api.put(`/daily-snippets/${snippet.id}`, { content });
    } else {
      await api.post('/daily-snippets', { content });
    }
    await loadSnippet(true);
  };

  const handleOrganize = async () => {
    if (!snippet?.date) return;

    setOrganizing(true);
    try {
      const res = await api.post<any>('/daily-snippets/organize', { date: snippet.date });
      setSnippet(res);
    } catch (err) {
      console.error('Failed to organize snippet', err);
    } finally {
      setOrganizing(false);
    }
  };

  function pushWithPreservedQuery(overrides: Record<string, string | number | null>) {
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    Object.entries(overrides).forEach(([k, v]) => {
      if (v == null) params.delete(k);
      else params.set(k, String(v));
    });
    router.push(`/daily-snippets?${params.toString()}`);
  }

  const goToSnippet = (id: number) => {
    pushWithPreservedQuery({ id });
  };

  if (loading) return (
    <div className="flex justify-center items-center min-h-[50vh]">
      <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 bg-mesh">
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <PageHeader
          title={snippet ? `Daily Snippet: ${snippet.date}` : '오늘의 스니펫'}
          description={snippet ? `${snippet.date} - 매일의 작은 기록을 남겨보세요.` : `${today} - 매일의 작은 기록을 남겨보세요.`}
          actions={
            <>
              <Button
                variant="outline"
                size="icon"
                disabled={!prevId}
                onClick={() => prevId && goToSnippet(prevId)}
                title="이전 스니펫"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                disabled={!nextId}
                onClick={() => nextId && goToSnippet(nextId)}
                title="다음 스니펫"
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          }
        />

        <Tabs value={viewParam} onValueChange={(v) => pushWithPreservedQuery({ view: v })} className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="my" className="gap-2">
              <User className="h-4 w-4" />
              나의 기록
            </TabsTrigger>
            <TabsTrigger value="team" className="gap-2">
              <Users className="h-4 w-4" />
              팀 피드
            </TabsTrigger>
          </TabsList>

          <TabsContent value="my" className="mt-0">
            <div className="w-full glass-card p-6 rounded-xl animate-entrance">
              <SnippetForm
                kind="daily"
                initialContent={snippet?.content || ''}
                onSave={handleSave}
                readOnly={readOnly}
                onOrganize={handleOrganize}
                isOrganizing={organizing}
                structuredContent={snippet?.structured}
                feedback={snippet?.feedback}
              />
            </div>
          </TabsContent>

          <TabsContent value="team" className="mt-0">
            <TeamSnippetFeed kind="daily" id={idParam ?? undefined} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default function DailySnippetsPage() {
  return (
    <Suspense fallback={<p>Loading…</p>}>
      <DailySnippetsContent />
    </Suspense>
  );
}
