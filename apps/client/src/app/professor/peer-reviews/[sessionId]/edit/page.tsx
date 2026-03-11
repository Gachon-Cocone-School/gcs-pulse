import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerReviewsMetadata } from '@/app/metadata';
import ProfessorPeerReviewsEditPageClient from './page.client';

export const metadata: Metadata = professorPeerReviewsMetadata;

interface ProfessorPeerReviewsEditPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function ProfessorPeerReviewsEditPage({ params }: ProfessorPeerReviewsEditPageProps) {
  const { sessionId } = await params;

  return (
    <Suspense>
      <ProfessorPeerReviewsEditPageClient sessionId={Number(sessionId)} />
    </Suspense>
  );
}
