'use client'

import React, { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { api } from '@/lib/api';
import SnippetForm from '@/components/views/SnippetForm';
import { Navigation } from '@/components/Navigation';
import { Button } from '@/components/Button';
import { Loader2 } from 'lucide-react';

function formatDateToYYYYMMDD(date: Date): string {
  return date.toISOString().split('T')[0];
}

function DailySnippetsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get('id');

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

      setReadOnly(currentDate < serverDate);

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

  const goToSnippet = (id: number) => {
    router.push(`/daily-snippets?id=${id}`);
  };

  if (loading) return (
    <div className="flex justify-center items-center min-h-[50vh]">
      <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
    </div>
  );

  return (
    <>
      <Navigation />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">
              {snippet ? `Daily Snippet: ${snippet.date}` : '오늘의 스니펫'}
            </h2>
            <p className="text-sm text-slate-600">
              {snippet ? snippet.date : today} - 매일의 작은 기록을 남겨보세요.
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              disabled={!prevId} 
              onClick={() => prevId && goToSnippet(prevId)}
            >
              ← 이전
            </Button>
            <Button 
              variant="outline" 
              disabled={!nextId} 
              onClick={() => nextId && goToSnippet(nextId)}
            >
              다음 →
            </Button>
          </div>
        </div>
        <div className="w-full">
          <SnippetForm 
            kind="daily" 
            initialContent={snippet?.content || ''} 
            onSave={handleSave}
            readOnly={readOnly}
            onOrganize={snippet?.id ? handleOrganize : undefined}
            isOrganizing={organizing}
            structuredContent={snippet?.structured}
            feedback={snippet?.feedback}
          />
        </div>
      </main>
    </>
  );
}

export default function DailySnippetsPage() {
  return (
    <Suspense fallback={<p>Loading…</p>}>
      <DailySnippetsContent />
    </Suspense>
  );
}
