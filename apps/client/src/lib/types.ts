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

export interface PeerEvaluationSessionCreateRequest {
  title: string;
}

export interface PeerEvaluationSessionUpdateRequest {
  title: string;
}

export interface PeerEvaluationSessionMemberItem {
  student_user_id: number;
  student_name: string;
  student_email: string;
  team_label: string;
}

export interface PeerEvaluationSessionResponse {
  id: number;
  title: string;
  raw_text?: string | null;
  professor_user_id: number;
  is_open: boolean;
  access_token: string;
  form_url: string;
  created_at: string;
  updated_at: string;
  members: PeerEvaluationSessionMemberItem[];
}

export interface PeerEvaluationSessionListItem {
  id: number;
  title: string;
  is_open: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
  submitted_evaluators: number;
}

export interface PeerEvaluationSessionListResponse {
  items: PeerEvaluationSessionListItem[];
  total: number;
}

export interface PeerEvaluationParseCandidateItem {
  student_user_id: number;
  student_name: string;
  student_email: string;
}

export interface PeerEvaluationParseUnresolvedItem {
  team_label: string;
  raw_name: string;
  reason: string;
  candidates: PeerEvaluationParseCandidateItem[];
}

export interface PeerEvaluationParsePreviewMember {
  team_label: string;
  raw_name: string;
  student_user_id: number;
  student_name: string;
  student_email: string;
}

export interface PeerEvaluationSessionMembersParseRequest {
  raw_text: string;
}

export interface PeerEvaluationSessionMembersParseResponse {
  teams: Record<string, PeerEvaluationParsePreviewMember[]>;
  unresolved_members: PeerEvaluationParseUnresolvedItem[];
}

export interface PeerEvaluationSessionMembersConfirmRequest {
  members: PeerEvaluationParsePreviewMember[];
  unresolved_members: PeerEvaluationParseUnresolvedItem[];
}

export interface PeerEvaluationSessionMembersConfirmResponse {
  session_id: number;
  members: PeerEvaluationSessionMemberItem[];
}

export interface PeerEvaluationSessionStatusUpdateRequest {
  is_open: boolean;
}

export interface PeerEvaluationSessionProgressItem {
  evaluator_user_id: number;
  evaluator_name: string;
  evaluator_email: string;
  team_label: string;
  has_submitted: boolean;
}

export interface PeerEvaluationSessionProgressResponse {
  session_id: number;
  is_open: boolean;
  evaluator_statuses: PeerEvaluationSessionProgressItem[];
}

export interface PeerEvaluationSubmissionEntry {
  evaluatee_user_id: number;
  contribution_percent: number;
  fit_yes_no: boolean;
}

export interface PeerEvaluationFormSubmitRequest {
  entries: PeerEvaluationSubmissionEntry[];
}

export interface PeerEvaluationEvaluatorStatusItem {
  evaluator_user_id: number;
  evaluator_name: string;
  has_submitted: boolean;
}

export interface PeerEvaluationFormSessionInfo {
  session_id: number;
  title: string;
  is_open: boolean;
}

export interface PeerEvaluationFormResponse {
  session: PeerEvaluationFormSessionInfo;
  me: CommentUser;
  team_members: CommentUser[];
  evaluator_statuses: PeerEvaluationEvaluatorStatusItem[];
  has_submitted: boolean;
}

export interface PeerEvaluationSubmissionRow {
  evaluator_user_id: number;
  evaluator_name: string;
  evaluatee_user_id: number;
  evaluatee_name: string;
  contribution_percent: number;
  fit_yes_no: boolean;
  updated_at: string;
}

export interface PeerEvaluationSessionResultsResponse {
  session_id: number;
  total_evaluators_submitted: number;
  total_rows: number;
  rows: PeerEvaluationSubmissionRow[];
  contribution_avg_by_evaluatee: Record<string, number | null>;
  fit_yes_ratio_by_evaluatee: Record<string, number | null>;
  fit_yes_ratio_by_evaluator: Record<string, number | null>;
}

export interface PeerEvaluationMySummaryResponse {
  session_id: number;
  my_received_contribution_avg: number;
  my_given_contribution_avg: number;
  my_fit_yes_ratio_received: number;
  my_fit_yes_ratio_given: number;
}

export interface PeerEvaluationSessionStatusSseEvent {
  session_id: number;
  is_open: boolean;
  updated_at: string;
}

export interface PeerEvaluationProgressUpdatedSseEvent {
  session_id: number;
  evaluator_user_id: number;
  updated_at: string;
}
