'use client';

import React from 'react';
import { api } from '@/lib/api';
import { TeamSnippetCard } from './TeamSnippetCard';
import { Loader2, Users } from 'lucide-react';

interface TeamSnippetFeedProps {
  kind: 'daily' | 'weekly';
}

export function TeamSnippetFeed({ kind }: TeamSnippetFeedProps) {
  const [snippets, setSnippets] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  const fetchTeamSnippets = React.useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
      const res = await api.get<any>(`${endpoint}?scope=team&limit=20`);
      setSnippets(res.items || []);
    } catch (err) {
      console.error('Failed to fetch team snippets', err);
    } finally {
      setLoading(false);
    }
  }, [kind]);

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

  if (snippets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-white rounded-xl border border-dashed border-slate-200">
        <Users className="w-12 h-12 mb-4 opacity-20" />
        <p>팀원들의 스니펫이 아직 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 grid-cols-1">
        {snippets.map((snippet) => (
          <TeamSnippetCard
            key={snippet.id}
            snippet={snippet}
            kind={kind}
            showDetails={false}
          />
        ))}
      </div>
    </div>
  );
}
