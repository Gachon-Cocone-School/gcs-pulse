import type { Metadata } from 'next';
import { professorABPracticeMetadata } from '@/app/metadata';
import ABPracticeCreatePageClient from '../../new/page.client';

export const metadata: Metadata = professorABPracticeMetadata;

export default async function ABPracticeEditPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ABPracticeCreatePageClient sessionId={Number(sessionId)} />;
}
