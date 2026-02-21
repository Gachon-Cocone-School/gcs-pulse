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

export type TeamLeaveResponse = {
  message: string;
};
