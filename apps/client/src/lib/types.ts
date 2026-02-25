export interface AuthConsent {
  term_id: number;
  agreed_at: string;
}

export type LeagueType = 'undergrad' | 'semester' | 'none';

export interface AuthUser {
  id?: number;
  email: string;
  name: string;
  picture?: string;
  roles: string[];
  email_verified: boolean;
  league_type: LeagueType;
  consents: AuthConsent[];
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

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
}
