export * from './types/auth';

export interface CommentUser {
  id: number;
  name: string;
  email: string;
  picture?: string;
}

export interface Comment {
  id: number;
  user_id: number;
  user: CommentUser;
  daily_snippet_id?: number;
  weekly_snippet_id?: number;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CommentListProps {
  dailySnippetId?: number;
  weeklySnippetId?: number;
  initialComments?: Comment[];
  highlightCommentId?: number;
}

export type NotificationType =
  | 'comment_on_my_snippet'
  | 'mention_in_comment'
  | 'comment_on_participated_snippet';

export interface NotificationItem {
  id: number;
  user_id: number;
  actor_user_id: number;
  actor_user?: CommentUser;
  type: NotificationType;
  daily_snippet_id?: number | null;
  weekly_snippet_id?: number | null;
  comment_id?: number | null;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface NotificationUnreadCountResponse {
  unread_count: number;
}

export interface NotificationReadAllResponse {
  updated_count: number;
}

export interface NotificationSetting {
  user_id: number;
  notify_post_author: boolean;
  notify_mentions: boolean;
  notify_participants: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationSettingUpdate {
  notify_post_author?: boolean;
  notify_mentions?: boolean;
  notify_participants?: boolean;
}
