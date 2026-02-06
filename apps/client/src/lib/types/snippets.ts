export type SnippetBase = {
  id: number;
  user_id: number;
  date: string; // daily: yyyy-mm-dd
  content: string;
  created_at: string;
  updated_at: string;
};
export type DailySnippetResponse = SnippetBase;
export type DailySnippetListResponse = { items: DailySnippetResponse[]; total: number; limit: number; offset: number };
export type DailySnippetCreate = { content: string };
export type DailySnippetUpdate = { content: string };
export type WeeklySnippetResponse = Omit<SnippetBase, 'date'> & { week: string };
export type WeeklySnippetListResponse = { items: WeeklySnippetResponse[]; total: number; limit: number; offset: number };
export type WeeklySnippetCreate = { content: string };
export type WeeklySnippetUpdate = { content: string };
