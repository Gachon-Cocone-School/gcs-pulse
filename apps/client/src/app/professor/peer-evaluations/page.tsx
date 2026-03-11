import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorPeerEvaluationsMetadata } from '@/app/metadata';
import ProfessorPeerEvaluationsPageClient from './page.client';

export const metadata: Metadata = professorPeerEvaluationsMetadata;

export default function ProfessorPeerEvaluationsPage() {
  return (
    <Suspense>
      <ProfessorPeerEvaluationsPageClient />
    </Suspense>
  );
}
