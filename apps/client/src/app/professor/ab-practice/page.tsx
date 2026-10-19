import type { Metadata } from 'next';
import { professorABPracticeMetadata } from '@/app/metadata';
import ABPracticeListPageClient from './page.client';

export const metadata: Metadata = professorABPracticeMetadata;

export default function ABPracticePage() {
  return <ABPracticeListPageClient />;
}
