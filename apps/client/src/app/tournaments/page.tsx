import type { Metadata } from 'next';
import { Suspense } from 'react';
import TournamentsPageClient from './page.client';

export const metadata: Metadata = {
  title: '토너먼트',
  description: '내가 참가한 토너먼트 대진표를 확인합니다.',
};

export default function TournamentsPage() {
  return (
    <Suspense>
      <TournamentsPageClient />
    </Suspense>
  );
}
