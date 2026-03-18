import type { Metadata } from 'next';
import { Suspense } from 'react';
import StudentTournamentBracketPageClient from './page.client';

export const metadata: Metadata = {
  title: '토너먼트 대진표',
  description: '토너먼트 전체 대진표를 확인합니다.',
};

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function StudentTournamentBracketPage({ params }: Props) {
  const { sessionId } = await params;
  return (
    <Suspense>
      <StudentTournamentBracketPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
