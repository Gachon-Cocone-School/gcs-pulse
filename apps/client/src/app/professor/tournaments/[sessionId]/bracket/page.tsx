import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorTournamentsMetadata } from '@/app/metadata';
import ProfessorTournamentBracketPageClient from './page.client';

export const metadata: Metadata = professorTournamentsMetadata;

interface ProfessorTournamentBracketPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorTournamentBracketPage({ params }: ProfessorTournamentBracketPageProps) {
  const { sessionId } = await params;
  const parsedSessionId = Number(sessionId);

  if (!Number.isFinite(parsedSessionId) || parsedSessionId <= 0) {
    throw new Error('Invalid session id');
  }

  return (
    <Suspense>
      <ProfessorTournamentBracketPageClient sessionId={parsedSessionId} />
    </Suspense>
  );
}
