import { achievementsMetadata } from '@/app/metadata';
import AchievementsPageClient from './page.client';

export const metadata = achievementsMetadata;

export default function AchievementsPage() {
  return <AchievementsPageClient />;
}
