import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsEditPageClient from '@/app/professor/peer-evaluations/[sessionId]/edit/page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerReviewsEditPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsEditPage({ params }: ProfessorPeerReviewsEditPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsEditPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
