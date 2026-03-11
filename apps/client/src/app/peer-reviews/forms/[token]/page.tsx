import type { Metadata } from 'next';
import { Suspense } from 'react';

import { peerEvaluationFormMetadata } from '@/app/metadata';
import PeerEvaluationFormPageClient from '@/app/peer-evaluations/forms/[token]/page.client';

export const metadata: Metadata = peerEvaluationFormMetadata;

interface PeerReviewFormPageProps {
  params: Promise<{
    token: string;
  }>;
}

export default async function PeerReviewFormPage({ params }: PeerReviewFormPageProps) {
  const { token } = await params;

  return (
    <Suspense>
      <PeerEvaluationFormPageClient token={token} />
    </Suspense>
  );
}
