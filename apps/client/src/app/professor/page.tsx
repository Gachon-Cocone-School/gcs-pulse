import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorSnippetsMetadata } from '@/app/metadata';
import ProfessorSnippetsPageClient from './page.client';

export const metadata: Metadata = professorSnippetsMetadata;

interface ProfessorSnippetsPageProps {
  searchParams: Promise<{
    kind?: string;
    id?: string;
    date?: string;
    week?: string;
    q?: string;
    student_user_id?: string;
    highlight_comment_id?: string;
    test_now?: string;
  }>;
}

export default async function ProfessorSnippetsPage({ searchParams }: ProfessorSnippetsPageProps) {
  const { kind, id, date, week, q, student_user_id, highlight_comment_id, test_now } = await searchParams;

  return (
    <Suspense>
      <ProfessorSnippetsPageClient
        kindParam={kind}
        idParam={id}
        dateParam={date}
        weekParam={week}
        queryParam={q}
        studentUserIdParam={student_user_id}
        highlightCommentIdParam={highlight_comment_id}
        testNowParam={test_now}
      />
    </Suspense>
  );
}
