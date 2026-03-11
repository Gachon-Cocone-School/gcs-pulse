import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsProgressPageClient from '@/app/professor/peer-evaluations/[sessionId]/progress/page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerReviewsProgressPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsProgressPage({ params }: ProfessorPeerReviewsProgressPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsProgressPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
