'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Sparkles } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

function escapeRegex(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) return text;
  const parts = text.split(new RegExp(`(${escapeRegex(keyword)})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === keyword.toLowerCase() ? (
      <mark
        key={i}
        className="bg-yellow-200 dark:bg-yellow-800/50 rounded-sm px-0.5 not-italic"
      >
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

interface SearchResultCardProps {
  snippet: any;
  kind: 'daily' | 'weekly';
  keyword: string;
}

export function SearchResultCard({ snippet, kind, keyword }: SearchResultCardProps) {
  const router = useRouter();

  const user = snippet.user;
  const dateLabel =
    kind === 'daily'
      ? format(new Date(snippet.date), 'yyyy년 M월 d일 (EEEE)', { locale: ko })
      : `${format(new Date(snippet.week), 'yyyy년 M월 d일', { locale: ko })} 주간`;

  const feedback = React.useMemo(() => {
    if (!snippet.feedback) return null;
    try {
      return typeof snippet.feedback === 'string'
        ? JSON.parse(snippet.feedback)
        : snippet.feedback;
    } catch {
      return null;
    }
  }, [snippet.feedback]);

  const handleClick = () => {
    const path = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
    router.push(`${path}?id=${snippet.id}`);
  };

  return (
    <Card
      className={cn(
        'overflow-hidden border-border transition-colors cursor-pointer',
        'hover:border-ring hover:shadow-sm',
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleClick();
      }}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-9 w-9 border border-border">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback>{user?.name?.charAt(0) || '?'}</AvatarFallback>
            </Avatar>
            <div>
              <div className="font-semibold text-foreground text-sm">{user?.name || 'Unknown'}</div>
              <div className="text-xs text-muted-foreground">{dateLabel}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                'text-[10px] font-medium px-1.5 py-0.5',
                kind === 'daily'
                  ? 'border-blue-200 text-blue-600 dark:border-blue-800 dark:text-blue-400'
                  : 'border-purple-200 text-purple-600 dark:border-purple-800 dark:text-purple-400',
              )}
            >
              {kind === 'daily' ? '일간' : '주간'}
            </Badge>
            {feedback && (
              <Badge
                variant="secondary"
                className="bg-primary/10 text-primary border-primary/20 flex items-center gap-1 px-2 py-0.5"
              >
                <Sparkles className="w-3 h-3" />
                <span className="font-bold text-xs">{feedback.total_score}점</span>
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-2">
        <p className="text-sm text-foreground leading-relaxed line-clamp-3 whitespace-pre-wrap">
          {highlightKeyword(snippet.content ?? '', keyword)}
        </p>
      </CardContent>
    </Card>
  );
}
