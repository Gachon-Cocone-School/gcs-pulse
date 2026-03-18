'use client';

import React from 'react';
import { api } from '@/lib/api';
import type { TeamSnippetCardData } from '@/lib/types';
import { TeamSnippetCard } from './TeamSnippetCard';
import { Loader2, Users } from 'lucide-react';

interface TeamSnippetFeedProps {
  kind: 'daily' | 'weekly';
  id?: string | number;
  date?: string;
  highlightCommentId?: number;
  commentType?: 'peer' | 'professor';
}

type TeamSnippet = TeamSnippetCardData & {
  id: number | string;
  [key: string]: unknown;
};

export function TeamSnippetFeed({ kind, id, date, highlightCommentId, commentType = 'peer' }: TeamSnippetFeedProps) {
  const [snippets, setSnippets] = React.useState<TeamSnippet[]>([]);
  const [loading, setLoading] = React.useState(true);

  const normalizedSnippetId = React.useMemo(() => {
    if (id == null) {
      return null;
    }

    const parsedId = Number(id);
    return Number.isFinite(parsedId) ? parsedId : null;
  }, [id]);

  React.useEffect(() => {
    let cancelled = false;

    const fetchTeamSnippets = async () => {
      setLoading(true);
      try {
        const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
        const params = new URLSearchParams({ scope: 'team', limit: '20' });
        if (id != null) {
          params.set('id', String(id));
        } else if (date != null) {
          const fromKey = kind === 'daily' ? 'from_date' : 'from_week';
          const toKey = kind === 'daily' ? 'to_date' : 'to_week';
          params.set(fromKey, date);
          params.set(toKey, date);
        }

        const res = await api.get<{ items?: TeamSnippet[] }>(`${endpoint}?${params.toString()}`);
        const items: TeamSnippet[] = Array.isArray(res?.items) ? res.items : [];

        if (normalizedSnippetId !== null) {
          const hasTargetSnippet = items.some((snippet) => Number(snippet?.id) === normalizedSnippetId);
          if (!hasTargetSnippet) {
            try {
              const targetSnippet = await api.get<TeamSnippet>(`${endpoint}/${normalizedSnippetId}`);
              if (!cancelled) {
                setSnippets([targetSnippet, ...items]);
              }
              return;
            } catch (fetchByIdError) {
              console.error('Failed to fetch highlighted snippet by id', fetchByIdError);
            }
          }
        }

        if (!cancelled) {
          setSnippets(items);
        }
      } catch (err) {
        console.error('Failed to fetch team snippets', err);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchTeamSnippets();

    return () => {
      cancelled = true;
    };
  }, [kind, id, date, normalizedSnippetId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  const visibleSnippets = snippets;
  const highlightSnippetId = normalizedSnippetId;

  if (visibleSnippets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground bg-card rounded-xl border border-dashed border-border">
        <Users className="w-12 h-12 mb-4 opacity-20" />
        <p>아직 표시할 스니펫이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 grid-cols-1">
        {visibleSnippets.map((snippet) => {
          const snippetId = Number(snippet.id);
          const normalizedSnippet = Number.isFinite(snippetId)
            ? { ...snippet, id: snippetId }
            : { ...snippet, id: undefined };

          return (
            <TeamSnippetCard
              key={snippet.id}
              snippet={normalizedSnippet}
              kind={kind}
              showDetails={true}
              highlightCommentId={
                highlightSnippetId !== null && Number(snippet.id) === highlightSnippetId
                  ? highlightCommentId
                  : undefined
              }
              commentType={commentType}
            />
          );
        })}
      </div>
    </div>
  );
}
