import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorTournamentsMetadata } from '@/app/metadata';
import ProfessorTournamentMatchProgressPageClient from './page.client';

export const metadata: Metadata = professorTournamentsMetadata;

interface ProfessorTournamentMatchProgressPageProps {
  params: Promise<{
    matchId: string;
  }>;
}

export default async function ProfessorTournamentMatchProgressPage({ params }: ProfessorTournamentMatchProgressPageProps) {
  const { matchId } = await params;
  const parsedMatchId = Number(matchId);

  if (!Number.isFinite(parsedMatchId) || parsedMatchId <= 0) {
    throw new Error('Invalid match id');
  }

  return (
    <Suspense>
      <ProfessorTournamentMatchProgressPageClient matchId={parsedMatchId} />
    </Suspense>
  );
}
