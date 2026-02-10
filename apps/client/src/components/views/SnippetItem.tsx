'use client';

import { DailySnippetResponse, WeeklySnippetResponse } from '@/lib/types/snippets';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';

interface SnippetItemProps {
  snippet: DailySnippetResponse | WeeklySnippetResponse;
  kind: 'daily' | 'weekly';
  currentUserId?: number | string;
  onDelete?: (id: number) => Promise<void>;
}

export default function SnippetItem({ snippet, kind, currentUserId, onDelete }: SnippetItemProps) {
  const router = useRouter();
  const numericCurrentUserId = currentUserId != null ? Number(currentUserId) : undefined;
  const isOwner = numericCurrentUserId !== undefined && numericCurrentUserId === snippet.user_id;
  const title = snippet.content.split('\n')[0] || (snippet.content.length > 50 ? snippet.content.slice(0, 50) + '...' : snippet.content);
  const excerpt = snippet.content.slice(0, 200) + (snippet.content.length > 200 ? '...' : '');
  const dateOrWeek = 'date' in snippet ? (snippet as DailySnippetResponse).date : (snippet as WeeklySnippetResponse).week;

  const handleView = () => router.push(`/${kind}-snippets/${snippet.id}`);
  const handleEdit = () => router.push(`/${kind}-snippets/${snippet.id}/edit`);
  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this snippet?')) {
      if (onDelete) await onDelete(snippet.id);
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
          <p className="text-sm text-slate-500">{dateOrWeek}</p>
          <div className="prose max-w-none dark:prose-invert mt-3 text-slate-700 line-clamp-3">{excerpt}</div>
        </div>
        <div className="flex-shrink-0 flex flex-col items-end gap-2">
          <div className="flex flex-col gap-2">
            <Button variant="outline" size="sm" onClick={handleView}>보기</Button>
            <Button variant="ghost" size="sm" onClick={handleEdit}>편집</Button>
            {isOwner && <Button variant="destructive" size="sm" onClick={handleDelete}>삭제</Button>}
          </div>
        </div>
      </div>
    </Card>
  );
}
