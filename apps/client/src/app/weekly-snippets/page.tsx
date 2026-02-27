import { weeklySnippetsMetadata } from "@/app/metadata";
import WeeklySnippetsPageClient from "./page.client";

export const metadata = weeklySnippetsMetadata;

interface WeeklySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    view?: string;
    highlight_comment_id?: string;
    test_now?: string;
  }>;
}

export default async function WeeklySnippetsPage({ searchParams }: WeeklySnippetsPageProps) {
  const { id, view, highlight_comment_id, test_now } = await searchParams;

  return (
    <WeeklySnippetsPageClient
      idParam={id}
      viewParam={view}
      highlightCommentIdParam={highlight_comment_id}
      testNowParam={test_now}
    />
  );
}
