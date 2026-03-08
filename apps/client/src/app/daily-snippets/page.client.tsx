'use client';

import { SnippetPageClient } from '@/components/views/SnippetPageClient';
import { toDateKey } from '@/lib/dateKeys';

interface DailySnippetsPageClientProps {
  idParam?: string;
  keyParam?: string;
  viewParam?: string;
  highlightCommentIdParam?: string;
  testNowParam?: string;
}

export default function DailySnippetsPageClient({
  idParam,
  keyParam,
  viewParam,
  highlightCommentIdParam,
  testNowParam,
}: DailySnippetsPageClientProps) {
  const baseNow = testNowParam ? new Date(testNowParam) : new Date();
  const today = toDateKey(baseNow);

  return (
    <SnippetPageClient
      kind="daily"
      idParam={idParam}
      keyParam={keyParam}
      viewParam={viewParam}
      highlightCommentIdParam={highlightCommentIdParam}
      testNowParam={testNowParam}
      fallbackKey={today}
    />
  );
}
