import type { Metadata } from 'next';

import { professorABPracticeMetadata } from '@/app/metadata';
import ABPracticeResultsPageClient from './page.client';

export const metadata: Metadata = professorABPracticeMetadata;

export default async function ABPracticeResultsPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ABPracticeResultsPageClient sessionId={Number(sessionId)} />;
}
