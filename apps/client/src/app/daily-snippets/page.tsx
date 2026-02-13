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

function formatDateToYYYYMMDD(date: Date): string {
  return date.toISOString().split('T')[0];
}

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

  const today = formatDateToYYYYMMDD(new Date());

  const loadSnippet = React.useCallback(async (silent = false) => {
    if (!silent) setLoading(true);

    // 1. Load the main snippet (either by ID or Today)
    try {
      let currentSnippet = null;
      let currentDate = today;
      let serverDate = today;

      // Start date fetch immediately
      const datePromise = api.get<{ date: string }>('/snippet_date').catch(e => {
        console.error('Failed to fetch server date', e);
        return null;
      });

      if (idParam) {
        // Parallel fetch if we have ID
        const [dateRes, snippetRes] = await Promise.all([
          datePromise,
          api.get(`/daily-snippets/${idParam}`).catch(e => {
            console.error('Failed to load snippet by ID', e);
            return null;
          })
        ]);

        if (dateRes && dateRes.date) {
          serverDate = dateRes.date;
        }
        currentSnippet = snippetRes;
      } else {
        // Sequential fetch if we depend on date
        const dateRes = await datePromise;
        if (dateRes && dateRes.date) {
          serverDate = dateRes.date;
        }

        try {
          const res = await api.get(`/daily-snippets?from_date=${serverDate}&to_date=${serverDate}&limit=1`) as any;
          const items = res?.items || [];
          if (items.length > 0) {
            currentSnippet = items[0];
          }
        } catch (e) {
           console.error('Failed to load today snippet', e);
        }
      }

      setSnippet(currentSnippet);

      if (currentSnippet?.date) {
        currentDate = currentSnippet.date;
      }

      // prefer server-provided editable flag when present
      const serverEditable = currentSnippet?.editable;
      if (serverEditable === undefined) {
        setReadOnly(currentDate < serverDate);
      } else {
        setReadOnly(!serverEditable);
      }

      const d = new Date(currentDate);

      const dPrev = new Date(d);
      dPrev.setDate(dPrev.getDate() - 1);
      const prevDateStr = formatDateToYYYYMMDD(dPrev);

      const dNext = new Date(d);
      dNext.setDate(dNext.getDate() + 1);
      const nextDateStr = formatDateToYYYYMMDD(dNext);

      const [prevRes, nextRes] = await Promise.all([
        api.get(`/daily-snippets?to_date=${prevDateStr}&order=desc&limit=1`) as Promise<any>,
        api.get(`/daily-snippets?from_date=${nextDateStr}&order=asc&limit=1`) as Promise<any>
      ]);

      const prevItems = prevRes?.items || [];
      const nextItems = nextRes?.items || [];

      setPrevId(prevItems.length > 0 ? prevItems[0].id : null);
      setNextId(nextItems.length > 0 ? nextItems[0].id : null);

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
