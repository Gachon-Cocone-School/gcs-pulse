import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsProgressPageClient from './page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerEvaluationsProgressPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerEvaluationsProgressPage({ params }: ProfessorPeerEvaluationsProgressPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsProgressPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
