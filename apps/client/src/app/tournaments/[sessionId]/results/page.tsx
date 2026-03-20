import type { Metadata } from 'next';
import { Suspense } from 'react';
import StudentTournamentResultsPageClient from './page.client';

export const metadata: Metadata = {
  title: '토너먼트 결과',
  description: '토너먼트 팀 순위 및 투표 결과를 확인합니다.',
};

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function StudentTournamentResultsPage({ params }: Props) {
  const { sessionId } = await params;
  return (
    <Suspense>
      <StudentTournamentResultsPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
