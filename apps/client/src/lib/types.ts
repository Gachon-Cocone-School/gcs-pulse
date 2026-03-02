export * from './types/auth';

export interface CommentUser {
  id: number;
  name: string;
  email: string;
  picture?: string;
}

export type CommentType = 'peer' | 'professor';

export interface Comment {
  id: number;
  user_id: number;
  user: CommentUser;
  daily_snippet_id?: number;
  weekly_snippet_id?: number;
  comment_type: CommentType;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CommentListProps {
  dailySnippetId?: number;
  weeklySnippetId?: number;
  initialComments?: Comment[];
  highlightCommentId?: number;
  commentType?: CommentType;
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

export type RiskBand = 'Low' | 'Medium' | 'High' | 'Critical';

export interface RiskReason {
  layer: string;
  risk_factor: string;
  prompt_items: string[];
  severity: string;
  impact: number;
  evidence: string;
  why_it_matters: string;
}

export interface RiskConfidence {
  score: number;
  data_coverage: number;
  signal_agreement: number;
  history_depth: number;
}

export interface RiskTonePolicy {
  primary: string;
  secondary: string[];
  suppressed: string[];
  trigger_patterns: string[];
  policy_confidence: number;
}

export interface StudentRiskSnapshot {
  user_id: number;
  evaluated_at: string;
  l1: number;
  l2: number;
  l3: number;
  risk_score: number;
  risk_band: RiskBand;
  daily_subscores: Record<string, number>;
  weekly_subscores: Record<string, number>;
  trend_subscores: Record<string, number>;
  confidence: RiskConfidence;
  reasons: RiskReason[];
  tone_policy: RiskTonePolicy;
  needs_professor_review: boolean;
}

export interface ProfessorOverviewResponse {
  high_or_critical_count: number;
  high_count: number;
  critical_count: number;
  medium_count: number;
  low_count: number;
}

export interface ProfessorRiskQueueItem {
  user_id: number;
  user_name: string;
  user_email: string;
  risk_score: number;
  risk_band: RiskBand;
  evaluated_at: string;
  confidence: number;
  reasons: RiskReason[];
  tone_policy?: RiskTonePolicy | null;
  latest_daily_snippet_id?: number | null;
  latest_weekly_snippet_id?: number | null;
}

export interface ProfessorRiskQueueResponse {
  items: ProfessorRiskQueueItem[];
  total: number;
}

export interface ProfessorRiskHistoryResponse {
  items: StudentRiskSnapshot[];
  total: number;
}

export interface ProfessorRiskEvaluateResponse {
  snapshot: StudentRiskSnapshot;
}
