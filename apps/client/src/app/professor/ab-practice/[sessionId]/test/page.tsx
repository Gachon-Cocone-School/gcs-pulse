import type { Metadata } from 'next';
import { professorABPracticeMetadata } from '@/app/metadata';
import ABPracticeSessionPageClient from '../page.client';

export const metadata: Metadata = professorABPracticeMetadata;

export default async function ABPracticeTestManagementPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ABPracticeSessionPageClient sessionId={Number(sessionId)} mode="test" />;
}
