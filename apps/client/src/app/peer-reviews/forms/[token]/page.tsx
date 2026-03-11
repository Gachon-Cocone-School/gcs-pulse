import type { Metadata } from 'next';
import { Suspense } from 'react';

import { peerReviewFormMetadata } from '@/app/metadata';
import PeerReviewFormPageClient from './page.client';

export const metadata: Metadata = peerReviewFormMetadata;

interface PeerReviewFormPageProps {
  params: Promise<{
    token: string;
  }>;
}

export default async function PeerReviewFormPage({ params }: PeerReviewFormPageProps) {
  const { token } = await params;

  return (
    <Suspense>
      <PeerReviewFormPageClient token={token} />
    </Suspense>
  );
}
