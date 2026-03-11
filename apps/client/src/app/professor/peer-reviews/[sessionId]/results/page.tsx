import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsResultsPageClient from '@/app/professor/peer-evaluations/[sessionId]/results/page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerReviewsResultsPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsResultsPage({ params }: ProfessorPeerReviewsResultsPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsResultsPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
