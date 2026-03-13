import type { Metadata } from 'next';
import { achievementsMetadata } from '@/app/metadata';
import { fetchWithCookie } from '@/lib/serverFetchWithCookie';
import type { MyAchievementGroupsResponse } from '@/lib/types/auth';
import AchievementsPageClient from './page.client';

export const metadata: Metadata = achievementsMetadata;

export default async function AchievementsPage() {
  const initialResponse = await fetchWithCookie<MyAchievementGroupsResponse>('/achievements/me');

  return <AchievementsPageClient initialItems={initialResponse?.items ?? null} />;
}
