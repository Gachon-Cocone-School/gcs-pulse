export interface User {
  id: number;
  sub: string;
  email: string;
  name: string;
  picture: string;
  roles: string[];
}

export interface Comment {
  id: number;
  user_id: number;
  user: User;
  daily_snippet_id?: number;
  weekly_snippet_id?: number;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CommentCreate {
  content: string;
  daily_snippet_id?: number;
  weekly_snippet_id?: number;
}
