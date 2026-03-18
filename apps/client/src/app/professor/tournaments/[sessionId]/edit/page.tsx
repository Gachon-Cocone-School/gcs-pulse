import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorTournamentsMetadata } from '@/app/metadata';
import ProfessorTournamentEditPageClient from './page.client';

export const metadata: Metadata = professorTournamentsMetadata;

interface ProfessorTournamentEditPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorTournamentEditPage({ params }: ProfessorTournamentEditPageProps) {
  const { sessionId } = await params;
  const parsedSessionId = sessionId === 'new' ? null : Number(sessionId);

  return (
    <Suspense>
      <ProfessorTournamentEditPageClient sessionId={Number.isFinite(parsedSessionId) ? parsedSessionId : null} />
    </Suspense>
  );
}
