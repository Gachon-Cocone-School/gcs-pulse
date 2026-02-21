import { weeklySnippetsMetadata } from "@/app/metadata";
import WeeklySnippetsPageClient from "./page.client";

export const metadata = weeklySnippetsMetadata;

interface WeeklySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    test_now?: string;
  }>;
}

export default async function WeeklySnippetsPage({ searchParams }: WeeklySnippetsPageProps) {
  const { id, test_now } = await searchParams;

  return <WeeklySnippetsPageClient idParam={id} testNowParam={test_now} />;
}
