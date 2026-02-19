'use client';

import React from 'react';
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
import { getWeekStartDateKey } from '@/lib/dateKeys';
import { loadSnippetPageData } from '@/lib/loadSnippetPageData';

interface WeeklySnippetsPageClientProps {
  idParam?: string;
}

export default function WeeklySnippetsPageClient({ idParam }: WeeklySnippetsPageClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { isAuthenticated, isLoading } = useAuth();
  const [snippet, setSnippet] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [organizing, setOrganizing] = React.useState(false);
  const [readOnly, setReadOnly] = React.useState(false);
  const [prevId, setPrevId] = React.useState<number | null>(null);
  const [nextId, setNextId] = React.useState<number | null>(null);

  const thisWeek = getWeekStartDateKey(new Date());

  const requestHeaders = React.useMemo<Record<string, string> | undefined>(() => {
    const value = searchParams.get('test_now');
    return value ? { 'x-test-now': value } : undefined;
  }, [searchParams]);

  const loadSnippet = React.useCallback(async (silent = false) => {
    if (!silent) setLoading(true);

    try {
      const result = await loadSnippetPageData({
        kind: 'weekly',
        idParam: idParam ?? null,
        fallbackKey: thisWeek,
        client: {
          get: (url) => api.get(url, { headers: requestHeaders }),
        },
        normalizeServerDate: (value) => getWeekStartDateKey(new Date(value)),
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
  }, [thisWeek, idParam, requestHeaders]);

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
      await api.put(`/weekly-snippets/${snippet.id}`, { content }, { headers: requestHeaders });
    } else {
      await api.post('/weekly-snippets', { content }, { headers: requestHeaders });
    }
    await loadSnippet(true);
  };

  const handleOrganize = async () => {
    if (!snippet?.week) return null;

    setOrganizing(true);
    try {
      const res = await api.post<any>('/weekly-snippets/organize', { week: snippet.week }, { headers: requestHeaders });
      setSnippet(res);
      return typeof res?.structured === 'string' ? res.structured : null;
    } catch (err) {
      console.error('Failed to organize weekly snippet', err);
      return null;
    } finally {
      setOrganizing(false);
    }
  };

  const goToSnippet = (id: number) => {
    router.push(`/weekly-snippets?id=${id}`);
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
          title={snippet ? `Weekly Snippet: ${snippet.week}` : '이번 주의 스니펫'}
          description={snippet ? `${snippet.week} 주차 - 이번 주의 핵심을 정리해보세요.` : `${thisWeek} 주차 - 이번 주의 핵심을 정리해보세요.`}
          actions={
            <>
              <Button
                variant="outline"
                size="icon"
                disabled={!prevId}
                onClick={() => prevId && goToSnippet(prevId)}
                title="이전 주"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                disabled={!nextId}
                onClick={() => nextId && goToSnippet(nextId)}
                title="다음 주"
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          }
        />

        <Tabs defaultValue="my" className="w-full">
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
                kind="weekly"
                initialContent={snippet?.content || ''}
                onSave={handleSave}
                readOnly={readOnly}
                onOrganize={snippet?.id ? handleOrganize : undefined}
                isOrganizing={organizing}
                structuredContent={snippet?.structured}
                feedback={snippet?.feedback}
              />
            </div>
          </TabsContent>

          <TabsContent value="team" className="mt-0">
            <TeamSnippetFeed kind="weekly" id={idParam} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
