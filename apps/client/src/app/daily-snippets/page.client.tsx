'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import SnippetForm from '@/components/views/SnippetForm';
import { Navigation } from '@/components/Navigation';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/PageHeader';
import { Loader2, ArrowLeft, ArrowRight, User, Users } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toDateKey } from '@/lib/dateKeys';
import { loadSnippetPageData } from '@/lib/loadSnippetPageData';

const TeamSnippetFeed = dynamic(
  () => import('@/components/views/TeamSnippetFeed').then((mod) => mod.TeamSnippetFeed),
  {
    loading: () => (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    ),
  },
);

interface DailySnippetsPageClientProps {
  idParam?: string;
  viewParam?: string;
  testNowParam?: string;
}

export default function DailySnippetsPageClient({
  idParam,
  viewParam,
  testNowParam,
}: DailySnippetsPageClientProps) {
  const router = useRouter();
  const activeView = viewParam ?? 'my';

  const { isAuthenticated, isLoading } = useAuth();
  const [snippet, setSnippet] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [organizing, setOrganizing] = React.useState(false);
  const [readOnly, setReadOnly] = React.useState(false);
  const [prevId, setPrevId] = React.useState<number | null>(null);
  const [nextId, setNextId] = React.useState<number | null>(null);

  const today = toDateKey(new Date());

  const requestHeaders = React.useMemo<Record<string, string> | undefined>(() => {
    return testNowParam ? { 'x-test-now': testNowParam } : undefined;
  }, [testNowParam]);

  const loadSnippet = React.useCallback(async (silent = false) => {
    if (!silent) setLoading(true);

    try {
      const result = await loadSnippetPageData({
        kind: 'daily',
        idParam: idParam ?? null,
        fallbackKey: today,
        client: {
          get: (url) => api.get(url, { headers: requestHeaders }),
        },
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
  }, [today, idParam, requestHeaders]);

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
      await api.put(`/daily-snippets/${snippet.id}`, { content }, { headers: requestHeaders });
    } else {
      await api.post('/daily-snippets', { content }, { headers: requestHeaders });
    }
    await loadSnippet(true);
  };

  const handleOrganize = async () => {
    setOrganizing(true);
    try {
      const res = await api.post<any>('/daily-snippets/organize', { date: snippet?.date }, { headers: requestHeaders });
      setSnippet(res);
      return typeof res?.structured === 'string' ? res.structured : null;
    } catch (err) {
      console.error('Failed to organize snippet', err);
      return null;
    } finally {
      setOrganizing(false);
    }
  };

  function pushWithPreservedQuery(overrides: Record<string, string | number | null>) {
    const params = new URLSearchParams(window.location.search);
    Object.entries(overrides).forEach(([k, v]) => {
      if (v == null) params.delete(k);
      else params.set(k, String(v));
    });
    router.push(`/daily-snippets?${params.toString()}`);
  }

  const goToSnippet = (id: number) => {
    pushWithPreservedQuery({ id });
  };

  const canGoBackToToday = typeof snippet?.date === 'string' && snippet.date < today;

  const handleGoToNextSnippet = () => {
    if (nextId) {
      goToSnippet(nextId);
      return;
    }

    if (canGoBackToToday) {
      pushWithPreservedQuery({ id: null });
    }
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
          title={snippet ? `일간 : ${snippet.date}` : `일간 :${today}`}
          description={snippet ? `매일의 작은 기록을 남겨보세요.` : `오늘의 작은 기록을 남겨보세요.`}
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
                disabled={!nextId && !canGoBackToToday}
                onClick={handleGoToNextSnippet}
                title="다음 스니펫"
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          }
        />

        <Tabs value={activeView} onValueChange={(v) => pushWithPreservedQuery({ view: v })} className="w-full">
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
            <TeamSnippetFeed kind="daily" id={idParam} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
