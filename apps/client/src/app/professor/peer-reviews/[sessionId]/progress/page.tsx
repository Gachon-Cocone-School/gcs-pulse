import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerReviewsMetadata } from '@/app/metadata';
import ProfessorPeerReviewsProgressPageClient from './page.client';

export const metadata: Metadata = professorPeerReviewsMetadata;

interface ProfessorPeerReviewsProgressPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsProgressPage({ params }: ProfessorPeerReviewsProgressPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerReviewsProgressPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
