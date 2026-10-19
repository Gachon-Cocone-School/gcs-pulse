import type { Metadata } from 'next';
import { professorABPracticeMetadata } from '@/app/metadata';
import ABPracticeCreatePageClient from './page.client';

export const metadata: Metadata = professorABPracticeMetadata;

export default function ABPracticeCreatePage() {
  return <ABPracticeCreatePageClient />;
}
