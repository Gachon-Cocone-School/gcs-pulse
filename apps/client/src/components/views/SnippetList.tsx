'use client';

import { DailySnippetResponse, WeeklySnippetResponse } from '@/lib/types/snippets';
import SnippetItem from './SnippetItem';
import { Card } from '@/components/Card';
import React from 'react';

interface SnippetListProps {
  items: (DailySnippetResponse | WeeklySnippetResponse)[];
  kind: 'daily' | 'weekly';
  currentUserId?: number;
  onDelete?: (id: number) => Promise<void>;
}

export default function SnippetList({ items, kind, currentUserId, onDelete }: SnippetListProps) {
  if (!items || items.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold">아직 스니펫이 없습니다</h3>
        <p className="text-sm text-slate-600 mt-1">첫 번째 스니펫을 작성해보세요.</p>

      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {items.map((snippet) => (
        <SnippetItem
          key={snippet.id}
          snippet={snippet}
          kind={kind}
          currentUserId={currentUserId}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
