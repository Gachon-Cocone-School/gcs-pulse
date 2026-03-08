'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ChevronDown, ChevronUp, Sparkles, Loader2 } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import SnippetPreview from '@/components/views/SnippetPreview';
import { cn } from '@/lib/utils';

const SnippetAnalysisReport = dynamic(
  () => import('./SnippetAnalysisReport').then((mod) => mod.SnippetAnalysisReport),
  {
    loading: () => <p className="text-sm text-muted-foreground">AI 분석을 불러오는 중입니다...</p>,
  },
);

const CommentList = dynamic(
  () => import('./CommentList').then((mod) => mod.CommentList),
  {
    loading: () => (
      <div className="flex justify-center py-4">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    ),
  },
);

interface TeamSnippetCardProps {
  snippet: any;
  kind: 'daily' | 'weekly';
  showDetails?: boolean;
  highlightCommentId?: number;
  commentType?: 'peer' | 'professor';
}

export function TeamSnippetCard({
  snippet,
  kind,
  showDetails = true,
  highlightCommentId,
  commentType = 'peer',
}: TeamSnippetCardProps) {
  // showDetails controls whether detailed section + toggle are rendered
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [showComments, setShowComments] = React.useState(false);

  React.useEffect(() => {
    if (highlightCommentId) {
      setShowComments(true);
      setIsExpanded(true);
    }
  }, [highlightCommentId]);

  const user = snippet.user;
  const dateLabel = kind === 'daily'
    ? format(new Date(snippet.date), 'yyyy년 M월 d일 (EEEE)', { locale: ko })
    : `${format(new Date(snippet.week), 'yyyy년 M월 d일', { locale: ko })} 주간`;

  const feedback = React.useMemo(() => {
    if (!snippet.feedback) return null;
    try {
      return typeof snippet.feedback === 'string'
        ? JSON.parse(snippet.feedback)
        : snippet.feedback;
    } catch (e) {
      return null;
    }
  }, [snippet.feedback]);

  return (
    <Card className="overflow-hidden border-border hover:border-ring transition-colors">
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10 border border-border">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback>{user?.name?.charAt(0) || '?'}</AvatarFallback>
            </Avatar>
            <div>
              <div className="font-semibold text-foreground">{user?.name || 'Unknown'}</div>
              <div className="text-xs text-muted-foreground">{dateLabel}</div>
            </div>
          </div>
          {feedback && (
            <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20 flex items-center gap-1 px-2 py-1">
              <Sparkles className="w-3 h-3" />
              <span className="font-bold">{feedback.total_score}점</span>
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-2">
        <div className={cn(!isExpanded && 'line-clamp-3')}>
          {/* Keep prose styling in SnippetPreview to avoid nested prose conflicts */}
          <SnippetPreview content={snippet.content} contentClassName="text-foreground text-sm leading-relaxed" />
        </div>
      </CardContent>

      {isExpanded && (
        <div className="mt-6 pt-6 border-t border-border">
          <CardContent className="p-4 pt-6">
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">AI Analysis</h4>
              <SnippetAnalysisReport feedback={feedback} />
            </div>
          </CardContent>
        </div>
      )}

      {showComments && (
        <div className="border-t border-border bg-muted/30">
          <CardContent className="p-4">
             <CommentList
               dailySnippetId={kind === 'daily' ? snippet.id : undefined}
               weeklySnippetId={kind === 'weekly' ? snippet.id : undefined}
               highlightCommentId={highlightCommentId}
               commentType={commentType}
             />
          </CardContent>
        </div>
      )}

      <CardFooter className="p-2 bg-muted/50 border-t border-border flex justify-between items-center px-4">
        <Button
          variant="ghost"
          size="sm"
          className={cn("text-muted-foreground hover:text-foreground gap-1.5", showComments && "bg-muted text-foreground")}
          onClick={() => setShowComments(!showComments)}
        >
          {showComments ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
          <span className="text-xs font-medium">
            댓글 {snippet.comments_count || 0}개
          </span>
        </Button>

        {showDetails && (
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground h-8 gap-1"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                접기
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                상세 보기
              </>
            )}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
