import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsEditPageClient from './page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

interface ProfessorPeerEvaluationsEditPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerEvaluationsEditPage({ params }: ProfessorPeerEvaluationsEditPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerEvaluationsEditPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
