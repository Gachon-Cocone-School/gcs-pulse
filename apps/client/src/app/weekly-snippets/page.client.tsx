'use client';

import { SnippetPageClient } from '@/components/views/SnippetPageClient';
import { getWeekStartDateKey } from '@/lib/dateKeys';

interface WeeklySnippetsPageClientProps {
  idParam?: string;
  keyParam?: string;
  viewParam?: string;
  highlightCommentIdParam?: string;
  testNowParam?: string;
}

export default function WeeklySnippetsPageClient({
  idParam,
  keyParam,
  viewParam,
  highlightCommentIdParam,
  testNowParam,
}: WeeklySnippetsPageClientProps) {
  const baseNow = testNowParam ? new Date(testNowParam) : new Date();
  const thisWeek = getWeekStartDateKey(baseNow);

  return (
    <SnippetPageClient
      kind="weekly"
      idParam={idParam}
      keyParam={keyParam}
      viewParam={viewParam}
      highlightCommentIdParam={highlightCommentIdParam}
      testNowParam={testNowParam}
      fallbackKey={thisWeek}
    />
  );
}
