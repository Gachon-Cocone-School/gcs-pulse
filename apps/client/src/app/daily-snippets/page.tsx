import { dailySnippetsMetadata } from "@/app/metadata";
import DailySnippetsPageClient from "./page.client";

export const metadata = dailySnippetsMetadata;

interface DailySnippetsPageProps {
  searchParams: Promise<{
    id?: string;
    date?: string;
    view?: string;
    highlight_comment_id?: string;
    test_now?: string;
  }>;
}

export default async function DailySnippetsPage({ searchParams }: DailySnippetsPageProps) {
  const { id, date, view, highlight_comment_id, test_now } = await searchParams;

  return (
    <DailySnippetsPageClient
      idParam={id}
      keyParam={date}
      viewParam={view}
      highlightCommentIdParam={highlight_comment_id}
      testNowParam={test_now}
    />
  );
}
