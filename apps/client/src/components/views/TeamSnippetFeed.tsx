'use client';

import React from 'react';
import { api } from '@/lib/api';
import { TeamSnippetCard } from './TeamSnippetCard';
import { Loader2, Users } from 'lucide-react';

interface TeamSnippetFeedProps {
  kind: 'daily' | 'weekly';
  id?: string | number;
  highlightCommentId?: number;
}

export function TeamSnippetFeed({ kind, id, highlightCommentId }: TeamSnippetFeedProps) {
  const [snippets, setSnippets] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  const fetchTeamSnippets = React.useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
      const params = new URLSearchParams({ scope: 'team', limit: '20' });
      if (id) params.set('id', String(id));
      const res = await api.get<any>(`${endpoint}?${params.toString()}`);
      setSnippets(res.items || []);
    } catch (err) {
      console.error('Failed to fetch team snippets', err);
    } finally {
      setLoading(false);
    }
  }, [kind, id]);

  React.useEffect(() => {
    fetchTeamSnippets();
  }, [fetchTeamSnippets]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    );
  }

  const visibleSnippets = snippets;
  const highlightSnippetId = typeof id === 'string' || typeof id === 'number' ? Number(id) : null;

  if (visibleSnippets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-white rounded-xl border border-dashed border-slate-200">
        <Users className="w-12 h-12 mb-4 opacity-20" />
        <p>아직 표시할 스니펫이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 grid-cols-1">
        {visibleSnippets.map((snippet) => (
            <TeamSnippetCard
              key={snippet.id}
              snippet={snippet}
              kind={kind}
              showDetails={true}
              highlightCommentId={
                highlightSnippetId !== null && Number(snippet.id) === highlightSnippetId
                  ? highlightCommentId
                  : undefined
              }
            />
          ))}
      </div>
    </div>
  );
}
