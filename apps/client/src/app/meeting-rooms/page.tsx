import type { Metadata } from 'next';

import { meetingRoomsMetadata } from '@/app/metadata';
import MeetingRoomsPageClient from './page.client';

export const metadata: Metadata = meetingRoomsMetadata;

interface MeetingRoomsPageProps {
  searchParams: Promise<{
    date?: string;
  }>;
}

export default async function MeetingRoomsPage({ searchParams }: MeetingRoomsPageProps) {
  const { date } = await searchParams;

  return <MeetingRoomsPageClient dateParam={date} />;
}
