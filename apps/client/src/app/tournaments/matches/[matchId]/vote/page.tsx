import type { Metadata } from 'next';
import { Suspense } from 'react';

import { tournamentVoteMetadata } from '@/app/metadata';
import TournamentMatchVotePageClient from './page.client';

export const metadata: Metadata = tournamentVoteMetadata;

interface TournamentMatchVotePageProps {
  params: Promise<{
    matchId: string;
  }>;
}

export default async function TournamentMatchVotePage({ params }: TournamentMatchVotePageProps) {
  const { matchId } = await params;
  const parsedMatchId = Number(matchId);

  if (!Number.isFinite(parsedMatchId) || parsedMatchId <= 0) {
    throw new Error('Invalid match id');
  }

  return (
    <Suspense>
      <TournamentMatchVotePageClient matchId={parsedMatchId} />
    </Suspense>
  );
}
