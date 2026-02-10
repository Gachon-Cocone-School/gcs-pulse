'use client';

import React from 'react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SnippetAnalysisReport } from './SnippetAnalysisReport';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import SnippetPreview from '@/components/views/SnippetPreview';
import { cn } from '@/lib/utils';

interface TeamSnippetCardProps {
  snippet: any;
  kind: 'daily' | 'weekly';
  showDetails?: boolean;
}

export function TeamSnippetCard({ snippet, kind, showDetails = true }: TeamSnippetCardProps) {
  // showDetails controls whether detailed section + toggle are rendered
  const [isExpanded, setIsExpanded] = React.useState(false);

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
    <Card className="overflow-hidden border-slate-200 hover:border-slate-300 transition-colors">
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10 border border-slate-100">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback>{user?.name?.charAt(0) || '?'}</AvatarFallback>
            </Avatar>
            <div>
              <div className="font-semibold text-slate-900">{user?.name || 'Unknown'}</div>
              <div className="text-xs text-slate-500">{dateLabel}</div>
            </div>
          </div>
          {feedback && (
            <Badge variant="secondary" className="bg-rose-50 text-rose-700 border-rose-100 flex items-center gap-1 px-2 py-1">
              <Sparkles className="w-3 h-3" />
              <span className="font-bold">{feedback.total_score}점</span>
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-2">
        <div className={cn(
          "prose max-w-none text-slate-700 text-sm leading-relaxed",
          !isExpanded && "line-clamp-3"
        )}>
          {/* Use shared SnippetPreview to ensure consistent prose styling */}
          <SnippetPreview content={snippet.content} />
        </div>

      </CardContent>

      {isExpanded && (
        <div className="mt-6 pt-6 border-t border-slate-100">
          <CardContent className="p-4 pt-6">
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Analysis</h4>
              <SnippetAnalysisReport feedback={feedback} />
            </div>
          </CardContent>
        </div>
      )}

      <CardFooter className="p-2 bg-slate-50/50 border-t border-slate-100 flex justify-center">
        {showDetails && (
          <Button
            variant="ghost"
            size="sm"
            className="text-slate-500 hover:text-slate-700 h-8 gap-1 w-full"
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
