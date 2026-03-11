import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsPageClient from '@/app/professor/peer-evaluations/page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

export default function ProfessorPeerReviewsPage() {
  return (
    <Suspense>
      <ProfessorPeerEvaluationsPageClient />
    </Suspense>
  );
}
