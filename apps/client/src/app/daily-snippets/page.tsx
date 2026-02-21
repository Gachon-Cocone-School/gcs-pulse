import { dailySnippetsMetadata } from "@/app/metadata";
import DailySnippetsPageClient from "./page.client";

export const metadata = dailySnippetsMetadata;

interface DailySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    view?: string;
    test_now?: string;
  }>;
}

export default async function DailySnippetsPage({ searchParams }: DailySnippetsPageProps) {
  const { id, view, test_now } = await searchParams;

  return <DailySnippetsPageClient idParam={id} viewParam={view} testNowParam={test_now} />;
}
