export type APIToken = {
  id: string;
  description: string;
  created_at: string;
  last_used_at: string | null;
};

export type APITokenCreateResponse = APIToken & {
  token: string;
};
