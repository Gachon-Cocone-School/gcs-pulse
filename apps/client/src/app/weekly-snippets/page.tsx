import { weeklySnippetsMetadata } from "@/app/metadata";
import WeeklySnippetsPageClient from "./page.client";

export const metadata = weeklySnippetsMetadata;

interface WeeklySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
  }>;
}

export default async function WeeklySnippetsPage({ searchParams }: WeeklySnippetsPageProps) {
  const { id } = await searchParams;

  return <WeeklySnippetsPageClient idParam={id} />;
}
