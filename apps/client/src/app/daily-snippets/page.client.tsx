'use client';

import React from 'react';
import { SnippetPageClient } from '@/components/views/SnippetPageClient';
import { toDateKey } from '@/lib/dateKeys';

interface DailySnippetsPageClientProps {
  idParam?: string;
  viewParam?: string;
  testNowParam?: string;
}

export default function DailySnippetsPageClient({
  idParam,
  viewParam,
  testNowParam,
}: DailySnippetsPageClientProps) {
  const today = toDateKey(new Date());

  return (
    <SnippetPageClient
      kind="daily"
      idParam={idParam}
      viewParam={viewParam}
      testNowParam={testNowParam}
      fallbackKey={today}
    />
  );
}
