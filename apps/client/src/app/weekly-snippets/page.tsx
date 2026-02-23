import { weeklySnippetsMetadata } from "@/app/metadata";
import WeeklySnippetsPageClient from "./page.client";

export const metadata = weeklySnippetsMetadata;

interface WeeklySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    view?: string;
    test_now?: string;
  }>;
}

export default async function WeeklySnippetsPage({ searchParams }: WeeklySnippetsPageProps) {
  const { id, view, test_now } = await searchParams;

  return <WeeklySnippetsPageClient idParam={id} viewParam={view} testNowParam={test_now} />;
}
