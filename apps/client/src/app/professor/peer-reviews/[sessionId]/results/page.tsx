import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerReviewsMetadata } from '@/app/metadata';
import ProfessorPeerReviewsResultsPageClient from './page.client';

export const metadata: Metadata = professorPeerReviewsMetadata;

interface ProfessorPeerReviewsResultsPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsResultsPage({ params }: ProfessorPeerReviewsResultsPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerReviewsResultsPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
