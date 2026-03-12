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

export interface PeerReviewSessionCreateRequest {
  title: string;
}

export interface PeerReviewSessionUpdateRequest {
  title: string;
}

export interface PeerReviewSessionMemberItem {
  student_user_id: number;
  student_name: string;
  student_email: string;
  team_label: string;
}

export interface PeerReviewSessionResponse {
  id: number;
  title: string;
  raw_text?: string | null;
  professor_user_id: number;
  is_open: boolean;
  access_token: string;
  form_url: string;
  created_at: string;
  updated_at: string;
  members: PeerReviewSessionMemberItem[];
}

export interface PeerReviewSessionListItem {
  id: number;
  title: string;
  is_open: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
  submitted_evaluators: number;
}

export interface PeerReviewSessionListResponse {
  items: PeerReviewSessionListItem[];
  total: number;
}

export interface PeerReviewParseCandidateItem {
  student_user_id: number;
  student_name: string;
  student_email: string;
}

export interface PeerReviewParseUnresolvedItem {
  team_label: string;
  raw_name: string;
  reason: string;
  candidates: PeerReviewParseCandidateItem[];
}

export interface PeerReviewParsePreviewMember {
  team_label: string;
  raw_name: string;
  student_user_id: number;
  student_name: string;
  student_email: string;
}

export interface PeerReviewSessionMembersParseRequest {
  raw_text: string;
}

export interface PeerReviewSessionMembersParseResponse {
  teams: Record<string, PeerReviewParsePreviewMember[]>;
  unresolved_members: PeerReviewParseUnresolvedItem[];
}

export interface PeerReviewSessionMembersConfirmRequest {
  members: PeerReviewParsePreviewMember[];
  unresolved_members: PeerReviewParseUnresolvedItem[];
}

export interface PeerReviewSessionMembersConfirmResponse {
  session_id: number;
  members: PeerReviewSessionMemberItem[];
}

export interface PeerReviewSessionStatusUpdateRequest {
  is_open: boolean;
}

export interface PeerReviewSessionProgressItem {
  evaluator_user_id: number;
  evaluator_name: string;
  evaluator_email: string;
  team_label: string;
  has_submitted: boolean;
}

export interface PeerReviewSessionProgressResponse {
  session_id: number;
  is_open: boolean;
  evaluator_statuses: PeerReviewSessionProgressItem[];
}

export interface PeerReviewSubmissionEntry {
  evaluatee_user_id: number;
  contribution_percent: number;
  fit_yes_no: boolean;
}

export interface PeerReviewFormSubmitRequest {
  entries: PeerReviewSubmissionEntry[];
}

export interface PeerReviewEvaluatorStatusItem {
  evaluator_user_id: number;
  evaluator_name: string;
  has_submitted: boolean;
}

export interface PeerReviewFormSessionInfo {
  session_id: number;
  title: string;
  is_open: boolean;
}

export interface PeerReviewFormResponse {
  session: PeerReviewFormSessionInfo;
  me: CommentUser;
  team_members: CommentUser[];
  evaluator_statuses: PeerReviewEvaluatorStatusItem[];
  has_submitted: boolean;
}

export interface PeerReviewSubmissionRow {
  evaluator_user_id: number;
  evaluator_name: string;
  evaluatee_user_id: number;
  evaluatee_name: string;
  contribution_percent: number;
  fit_yes_no: boolean;
  updated_at: string;
}

export interface PeerReviewAggregatedStatItem {
  user_id: number;
  name: string;
  value: number | null;
}

export interface PeerReviewSessionResultsResponse {
  session_id: number;
  total_evaluators_submitted: number;
  total_rows: number;
  rows: PeerReviewSubmissionRow[];
  contribution_avg_by_evaluatee: PeerReviewAggregatedStatItem[];
  fit_yes_ratio_by_evaluatee: PeerReviewAggregatedStatItem[];
  fit_yes_ratio_by_evaluator: PeerReviewAggregatedStatItem[];
}

export interface PeerReviewMySummaryResponse {
  session_id: number;
  my_received_contribution_avg: number;
  my_given_contribution_avg: number;
  my_fit_yes_ratio_received: number;
  my_fit_yes_ratio_given: number;
}

export interface PeerReviewSessionStatusSseEvent {
  session_id: number;
  is_open: boolean;
  updated_at: string;
}

export interface PeerReviewProgressUpdatedSseEvent {
  session_id: number;
  evaluator_user_id: number;
  updated_at: string;
}

export interface ProfessorStudentSearchItem {
  student_user_id: number;
  student_name: string;
  student_email: string;
  team_name?: string | null;
}

export interface ProfessorStudentSearchResponse {
  items: ProfessorStudentSearchItem[];
  total: number;
}

export interface SnippetUser {
  id?: number;
  name?: string;
  email?: string;
  picture?: string;
}

export interface TeamSnippetCardData {
  id?: number;
  content?: string;
  date?: string;
  week?: string;
  feedback?: unknown;
  comments_count?: number;
  user?: SnippetUser | null;
}

export interface ProfessorSnippetPageDataResponse {
  snippet?: TeamSnippetCardData | null;
  read_only: boolean;
  prev_id?: number | null;
  next_id?: number | null;
}

