import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorTournamentsMetadata } from '@/app/metadata';
import ProfessorTournamentResultsPageClient from './page.client';

export const metadata: Metadata = professorTournamentsMetadata;

interface ProfessorTournamentResultsPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorTournamentResultsPage({ params }: ProfessorTournamentResultsPageProps) {
  const { sessionId } = await params;
  const parsedSessionId = Number(sessionId);

  if (!Number.isFinite(parsedSessionId) || parsedSessionId <= 0) {
    throw new Error('Invalid session id');
  }

  return (
    <Suspense>
      <ProfessorTournamentResultsPageClient sessionId={parsedSessionId} />
    </Suspense>
  );
}
