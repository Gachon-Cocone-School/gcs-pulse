import type { Metadata } from 'next';
import { abPracticeStudentMetadata } from '@/app/metadata';
import ABPracticeUploadPageClient from './page.client';

export const metadata: Metadata = abPracticeStudentMetadata;

export default async function ABPracticeUploadPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <ABPracticeUploadPageClient token={token} />;
}
