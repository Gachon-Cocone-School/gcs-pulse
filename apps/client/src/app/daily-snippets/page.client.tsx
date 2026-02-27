'use client';

import React from 'react';
import { SnippetPageClient } from '@/components/views/SnippetPageClient';
import { toDateKey } from '@/lib/dateKeys';

interface DailySnippetsPageClientProps {
  idParam?: string;
  viewParam?: string;
  highlightCommentIdParam?: string;
  testNowParam?: string;
}

export default function DailySnippetsPageClient({
  idParam,
  viewParam,
  highlightCommentIdParam,
  testNowParam,
}: DailySnippetsPageClientProps) {
  const today = toDateKey(new Date());

  return (
    <SnippetPageClient
      kind="daily"
      idParam={idParam}
      viewParam={viewParam}
      highlightCommentIdParam={highlightCommentIdParam}
      testNowParam={testNowParam}
      fallbackKey={today}
    />
  );
}
