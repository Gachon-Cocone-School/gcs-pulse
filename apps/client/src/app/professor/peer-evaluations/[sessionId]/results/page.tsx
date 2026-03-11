import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsResultsPageClient from './page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerEvaluationsResultsPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerEvaluationsResultsPage({ params }: ProfessorPeerEvaluationsResultsPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsResultsPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
