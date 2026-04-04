export type LeagueType = 'undergrad' | 'semester' | 'none';

export type UserConsent = {
  term_id: number;
  agreed_at: string;
};

export type AuthUser = {
  name: string;
  email: string;
  picture: string | null;
  email_verified: boolean;
  roles: string[];
  league_type: LeagueType;
  consents: UserConsent[];
  is_provisional: boolean;
};

export function hasPrivilegedRole(roles: readonly string[] | null | undefined) {
  return Boolean(roles?.some((role) => role === 'gcs' || role === '교수' || role === 'admin'));
}

export function hasGcsRole(roles: readonly string[] | null | undefined) {
  return Boolean(roles?.includes('gcs'));
}

export type TokenUsageShort = {
  allocated: number;
  used: number;
  remaining: number;
  last_reset: string;
  next_reset: string;
};

export type TokenUsageWeekly = {
  total_quota: number;
  total_used: number;
  total_remaining: number;
  per_user_allocated: number;
  last_reset: string;
  next_reset: string;
};

export type TokenUsageResponse = {
  short: TokenUsageShort;
  weekly: TokenUsageWeekly;
};

export type AuthStatusResponse = {
  authenticated: boolean;
  user: AuthUser | null;
};

export type AuthContextType = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string | null;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
};

export type APIToken = {
  id: string;
  description: string;
  created_at: string;
  last_used_at: string | null;
};

export type APITokenCreateResponse = APIToken & {
  token: string;
};

export type TeamMember = {
  id: number;
  name: string;
  email: string;
  picture: string | null;
};

export type Team = {
  id: number;
  name: string;
  invite_code: string | null;
  league_type: LeagueType;
  created_at: string;
  members: TeamMember[];
};

export type TeamMeResponse = {
  team: Team | null;
};

export type TeamCreateRequest = {
  name: string;
};

export type TeamJoinRequest = {
  invite_code: string;
};

export type TeamRenameRequest = {
  name: string;
};

export type TeamLeagueUpdateRequest = {
  league_type: LeagueType;
};

export type TeamLeaveResponse = {
  message: string;
};

export type MeLeagueResponse = {
  league_type: LeagueType;
  can_update: boolean;
  managed_by_team: boolean;
};

export type MeLeagueUpdateRequest = {
  league_type: LeagueType;
};

export type LeaderboardPeriod = 'daily' | 'weekly';

export type LeaderboardWindow = {
  label: 'yesterday' | 'last_week';
  key: string;
};

export type LeaderboardItem = {
  rank: number;
  score: number;
  participant_type: 'individual' | 'team';
  participant_id: number;
  participant_name: string;
  member_count?: number;
  submitted_count?: number;
};

export type LeaderboardResponse = {
  period: LeaderboardPeriod;
  window: LeaderboardWindow;
  league_type: LeagueType;
  excluded_by_league: boolean;
  items: LeaderboardItem[];
  total: number;
};

export type AchievementRarity = 'legend' | 'epic' | 'rare' | 'uncommon' | 'common';

export type MyAchievementGroupItem = {
  achievement_definition_id: number;
  code: string;
  name: string;
  description: string;
  badge_image_url: string;
  rarity: AchievementRarity | string;
  grant_count: number;
  last_granted_at: string;
};

export type MyAchievementGroupsResponse = {
  items: MyAchievementGroupItem[];
  total: number;
};

export type RecentAchievementGrantItem = {
  grant_id: number;
  user_id: number;
  user_name: string;
  achievement_definition_id: number;
  achievement_code: string;
  achievement_name: string;
  achievement_description: string;
  badge_image_url: string;
  rarity: AchievementRarity | string;
  granted_at: string;
  publish_start_at: string;
  publish_end_at: string | null;
};

export type RecentAchievementGrantsResponse = {
  items: RecentAchievementGrantItem[];
  total: number;
  limit: number;
};
