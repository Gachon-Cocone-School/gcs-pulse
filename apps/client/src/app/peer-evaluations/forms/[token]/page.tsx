import type { Metadata } from 'next';
import { Suspense } from 'react';

import { peerEvaluationFormMetadata } from '@/app/metadata';
import PeerEvaluationFormPageClient from './page.client';

export const metadata: Metadata = peerEvaluationFormMetadata;

interface PeerEvaluationFormPageProps {
  params: Promise<{
    token: string;
  }>;
}

export default async function PeerEvaluationFormPage({ params }: PeerEvaluationFormPageProps) {
  const { token } = await params;

  return (
    <Suspense>
      <PeerEvaluationFormPageClient token={token} />
    </Suspense>
  );
}
