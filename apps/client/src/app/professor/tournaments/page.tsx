import type { Metadata } from 'next';
import { Suspense } from 'react';

import { professorTournamentsMetadata } from '@/app/metadata';
import ProfessorTournamentsPageClient from './page.client';

export const metadata: Metadata = professorTournamentsMetadata;

export default function ProfessorTournamentsPage() {
  return (
    <Suspense>
      <ProfessorTournamentsPageClient />
    </Suspense>
  );
}
