import type { Metadata } from "next";
import { homeMetadata } from "@/app/metadata";
import { fetchWithCookie } from "@/lib/serverFetchWithCookie";
import type {
  LeaderboardResponse,
  RecentAchievementGrantsResponse,
} from "@/lib/types/auth";
import HomePageClient from "./page.client";

export const metadata: Metadata = homeMetadata;

export default async function HomePage() {
  const [initialLeaderboardDaily, initialRecentAchievementsResponse] = await Promise.all([
    fetchWithCookie<LeaderboardResponse>("/leaderboards?period=daily"),
    fetchWithCookie<RecentAchievementGrantsResponse>("/achievements/recent?limit=20"),
  ]);

  return (
    <HomePageClient
      initialLeaderboardDaily={initialLeaderboardDaily}
      initialRecentAchievements={initialRecentAchievementsResponse?.items ?? null}
    />
  );
}
