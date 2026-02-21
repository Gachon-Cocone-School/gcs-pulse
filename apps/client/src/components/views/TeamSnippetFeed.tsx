'use client';

import React from 'react';
import { api } from '@/lib/api';
import { TeamSnippetCard } from './TeamSnippetCard';
import { Loader2, Users } from 'lucide-react';
import { useAuth } from '@/context/auth-context';

interface TeamSnippetFeedProps {
  kind: 'daily' | 'weekly';
  id?: string | number;
}

export function TeamSnippetFeed({ kind, id }: TeamSnippetFeedProps) {
  const [snippets, setSnippets] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const { user, isLoading: authLoading } = useAuth();

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
  }, [kind, user]);

  // isSameUser compares multiple identifier fields to detect the current authenticated user
  function isSameUser(snippetUser: any, authUser: any) {
    if (!snippetUser || !authUser) return false;
    const keys = ['sub', 'google_sub', 'id', 'email'];
    for (const k of keys) {
      if (snippetUser[k] && authUser[k] && snippetUser[k] === authUser[k]) return true;
    }
    return false;
  }

  React.useEffect(() => {
    fetchTeamSnippets();
  }, [fetchTeamSnippets]);

  if (loading || authLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    );
  }

  const visibleSnippets = snippets;

  if (visibleSnippets.length === 0) {
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
        {visibleSnippets.map((snippet) => (
            <TeamSnippetCard
              key={snippet.id}
              snippet={snippet}
              kind={kind}
              showDetails={true}
            />
          ))}
      </div>
    </div>
  );
}
