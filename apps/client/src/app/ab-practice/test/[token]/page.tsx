import type { Metadata } from 'next';
import { abPracticeStudentMetadata } from '@/app/metadata';
import ABPracticeTestPageClient from './page.client';

export const metadata: Metadata = abPracticeStudentMetadata;

export default async function ABPracticeTestPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <ABPracticeTestPageClient token={token} />;
}
