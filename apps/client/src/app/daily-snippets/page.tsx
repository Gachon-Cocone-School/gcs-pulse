import { dailySnippetsMetadata } from "@/app/metadata";
import DailySnippetsPageClient from "./page.client";

export const metadata = dailySnippetsMetadata;

interface DailySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    view?: string;
  }>;
}

export default async function DailySnippetsPage({ searchParams }: DailySnippetsPageProps) {
  const { id, view } = await searchParams;

  return <DailySnippetsPageClient idParam={id} viewParam={view} />;
}
