import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerReviewsMetadata } from '@/app/metadata';
import ProfessorPeerReviewsPageClient from './page.client';

export const metadata: Metadata = professorPeerReviewsMetadata;

export default function ProfessorPeerReviewsPage() {
  return (
    <Suspense>
      <ProfessorPeerReviewsPageClient />
    </Suspense>
  );
}
