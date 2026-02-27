'use client';

import React from 'react';
import { SnippetPageClient } from '@/components/views/SnippetPageClient';
import { getWeekStartDateKey } from '@/lib/dateKeys';

interface WeeklySnippetsPageClientProps {
  idParam?: string;
  viewParam?: string;
  testNowParam?: string;
}

export default function WeeklySnippetsPageClient({
  idParam,
  viewParam,
  testNowParam,
}: WeeklySnippetsPageClientProps) {
  const thisWeek = getWeekStartDateKey(new Date());

  return (
    <SnippetPageClient
      kind="weekly"
      idParam={idParam}
      viewParam={viewParam}
      testNowParam={testNowParam}
      fallbackKey={thisWeek}
    />
  );
}
