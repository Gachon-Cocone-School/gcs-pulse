import { toast } from 'sonner';

import { ApiError, normalizeErrorMessage } from './apiErrors';
import { fetchWithRetry } from './fetchWithRetry';
import { getCsrfToken, hasBearerAuthorization, isUnsafeMethod } from './csrf';
import type {
  MentionableUser,
  MeetingRoom,
  MeetingRoomReservation,
  MeetingRoomReservationCreateRequest,
  MessageResponse,
  NotificationItem,
  NotificationListResponse,
  NotificationReadAllResponse,
  NotificationSetting,
  NotificationSettingUpdate,
  NotificationUnreadCountResponse,
  PeerReviewFormResponse,
  PeerReviewFormSubmitRequest,
  PeerReviewMySummaryResponse,
  PeerReviewSessionCreateRequest,
  PeerReviewSessionMembersConfirmRequest,
  PeerReviewSessionMembersConfirmResponse,
  PeerReviewSessionMembersParseRequest,
  PeerReviewSessionMembersParseResponse,
  PeerReviewSessionListResponse,
  PeerReviewSessionProgressResponse,
  PeerReviewSessionResponse,
  PeerReviewSessionResultsResponse,
  PeerReviewProgressUpdatedSseEvent,
  PeerReviewSessionStatusSseEvent,
  PeerReviewSessionStatusUpdateRequest,
  PeerReviewSessionUpdateRequest,
  ProfessorSnippetPageDataResponse,
  ProfessorStudentSearchResponse,
  TournamentBracketResponse,
  TournamentFormatParseRequest,
  TournamentFormatParseResponse,
  TournamentMatchItem,
  TournamentMatchProgressResponse,
  TournamentMatchStatusSseEvent,
  TournamentMatchStatusUpdateRequest,
  TournamentMatchWinnerUpdateRequest,
  TournamentSessionCreateRequest,
  TournamentSessionListResponse,
  TournamentSessionResponse,
  TournamentSessionStatusUpdateRequest,
  TournamentSessionUpdateRequest,
  TournamentTeamsConfirmRequest,
  TournamentTeamsConfirmResponse,
  TournamentTeamsParseRequest,
  TournamentTeamsParseResponse,
  TournamentVoteResponse,
  TournamentVoteSubmitRequest,
} from './types';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export { ApiError };

async function requestWithCommonOptions(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const url = `${API_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const method = (options.method || 'GET').toUpperCase();

  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined && options.body !== null;
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (isUnsafeMethod(method) && !hasBearerAuthorization(headers)) {
    const csrfToken = await getCsrfToken(API_URL);
    headers.set('X-CSRF-Token', csrfToken);
  }

  try {
    return await fetchWithRetry(url, {
      ...options,
      credentials: 'include',
      headers,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }

    const networkErrorMessage = '네트워크 요청에 실패했습니다. API 연결 상태와 브라우저 CORS 설정을 확인해 주세요.';

    if (error instanceof ApiError) {
      if (error.status === 0) {
        const normalizedMessage = error.message?.trim() || networkErrorMessage;
        const isBrowserNetworkError = /load failed|failed to fetch|network request failed/i.test(normalizedMessage);
        if (isBrowserNetworkError) {
          toast.error(networkErrorMessage, {
            id: 'network-error',
          });
          throw new ApiError(networkErrorMessage, 0);
        }
      }
      throw error;
    }

    toast.error(networkErrorMessage, {
      id: 'network-error',
    });
    console.error(`API Request Failed: ${method} ${url}`, error);
    throw new ApiError(networkErrorMessage, 0);
  }
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await requestWithCommonOptions(endpoint, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const fallbackMessage = `Error ${response.status}: ${response.statusText}`;
    const normalizedMessage = normalizeErrorMessage(errorData.detail ?? errorData.message, fallbackMessage);

    let errorMessage = normalizedMessage;
    if (errorMessage === fallbackMessage) {
      errorMessage = '요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
    }

    if (response.status === 401) {
      // For auth/me, we might want to just return authenticated: false
      if (endpoint.includes('/auth/me')) {
        return { authenticated: false, user: null } as any;
      }
    } else {
      // Global error notification for non-401 errors
      // Use message as id to prevent duplicate toasts for the same error
      toast.error(errorMessage, {
        id: errorMessage,
      });
    }

    throw new ApiError(errorMessage, response.status);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  request: (endpoint: string, options?: RequestInit) => requestWithCommonOptions(endpoint, options),

  get: <T>(endpoint: string, options?: RequestInit) =>
    apiFetch<T>(endpoint, { ...options, method: 'GET' }),

  post: <T, B = any>(endpoint: string, data?: B, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T, B = any>(endpoint: string, data?: B, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T, B = any>(endpoint: string, data?: B, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestInit) =>
    apiFetch<T>(endpoint, { ...options, method: 'DELETE' }),

  getMentionableUsers: (params: { dailySnippetId?: number; weeklySnippetId?: number }) => {
    const searchParams = new URLSearchParams();
    if (params.dailySnippetId) searchParams.set('daily_snippet_id', String(params.dailySnippetId));
    if (params.weeklySnippetId) searchParams.set('weekly_snippet_id', String(params.weeklySnippetId));
    return apiFetch<MentionableUser[]>(`/comments/mentionable-users?${searchParams}`);
  },
};

export const notificationsApi = {
  list: (params?: { limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (typeof params?.limit === 'number') searchParams.set('limit', String(params.limit));
    if (typeof params?.offset === 'number') searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    const endpoint = query ? `/notifications?${query}` : '/notifications';
    return api.get<NotificationListResponse>(endpoint);
  },

  unreadCount: () => api.get<NotificationUnreadCountResponse>('/notifications/unread-count'),

  markRead: (notificationId: number) =>
    api.patch<NotificationItem>(`/notifications/${notificationId}/read`),

  markAllRead: () => api.patch<NotificationReadAllResponse>('/notifications/read-all'),

  getSettings: () => api.get<NotificationSetting>('/notifications/settings'),

  updateSettings: (payload: NotificationSettingUpdate) =>
    api.patch<NotificationSetting, NotificationSettingUpdate>('/notifications/settings', payload),
};

export const professorApi = {
  searchStudents: (query: string, limit = 20) => {
    const params = new URLSearchParams();
    params.set('q', query);
    params.set('limit', String(limit));
    return api.get<ProfessorStudentSearchResponse>(`/users/students/search?${params.toString()}`);
  },

  getDailySnippetPageData: (params: { studentUserId: number; id?: string | null; date?: string | null }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('student_user_id', String(params.studentUserId));
    if (params.id) searchParams.set('id', params.id);
    if (params.date) searchParams.set('date', params.date);
    return api.get<ProfessorSnippetPageDataResponse>(
      `/daily-snippets/professor/page-data?${searchParams.toString()}`,
    );
  },

  getWeeklySnippetPageData: (params: { studentUserId: number; id?: string | null; week?: string | null }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('student_user_id', String(params.studentUserId));
    if (params.id) searchParams.set('id', params.id);
    if (params.week) searchParams.set('week', params.week);
    return api.get<ProfessorSnippetPageDataResponse>(
      `/weekly-snippets/professor/page-data?${searchParams.toString()}`,
    );
  },
};

export const meetingRoomsApi = {
  listRooms: () => api.get<MeetingRoom[]>('/meeting-rooms'),

  listReservations: (roomId: number, date: string) =>
    api.get<MeetingRoomReservation[]>(`/meeting-rooms/${roomId}/reservations?date=${encodeURIComponent(date)}`),

  createReservation: async (roomId: number, payload: MeetingRoomReservationCreateRequest) => {
    try {
      return await api.post<MeetingRoomReservation, MeetingRoomReservationCreateRequest>(
        `/meeting-rooms/${roomId}/reservations`,
        payload,
      );
    } catch (error) {
      if (error instanceof ApiError && /overlaps with an existing booking/i.test(error.message)) {
        throw new ApiError('선택한 시간대에 이미 예약이 있습니다. 다른 시간을 선택해 주세요.', error.status);
      }
      throw error;
    }
  },

  cancelReservation: (reservationId: number) =>
    api.delete<MessageResponse>(`/meeting-rooms/reservations/${reservationId}`),
};

export const peerReviewsApi = {
  listSessions: () => api.get<PeerReviewSessionListResponse>('/peer-reviews/sessions'),

  createSession: (payload: PeerReviewSessionCreateRequest) =>
    api.post<PeerReviewSessionResponse, PeerReviewSessionCreateRequest>(
      '/peer-reviews/sessions',
      payload,
    ),

  updateSession: (sessionId: number, payload: PeerReviewSessionUpdateRequest) =>
    api.patch<PeerReviewSessionResponse, PeerReviewSessionUpdateRequest>(
      `/peer-reviews/sessions/${sessionId}`,
      payload,
    ),

  deleteSession: (sessionId: number) =>
    api.delete<MessageResponse>(`/peer-reviews/sessions/${sessionId}`),

  parseMembersDraft: (payload: PeerReviewSessionMembersParseRequest, options?: RequestInit) =>
    api.post<PeerReviewSessionMembersParseResponse, PeerReviewSessionMembersParseRequest>(
      '/peer-reviews/members:parse',
      payload,
      options,
    ),

  parseMembers: (
    sessionId: number,
    payload: PeerReviewSessionMembersParseRequest,
    options?: RequestInit,
  ) =>
    api.post<PeerReviewSessionMembersParseResponse, PeerReviewSessionMembersParseRequest>(
      `/peer-reviews/sessions/${sessionId}/members:parse`,
      payload,
      options,
    ),

  confirmMembers: (sessionId: number, payload: PeerReviewSessionMembersConfirmRequest) =>
    api.post<PeerReviewSessionMembersConfirmResponse, PeerReviewSessionMembersConfirmRequest>(
      `/peer-reviews/sessions/${sessionId}/members:confirm`,
      payload,
    ),

  getSession: (sessionId: number) => api.get<PeerReviewSessionResponse>(`/peer-reviews/sessions/${sessionId}`),

  updateSessionStatus: (sessionId: number, payload: PeerReviewSessionStatusUpdateRequest) =>
    api.patch<PeerReviewSessionResponse, PeerReviewSessionStatusUpdateRequest>(
      `/peer-reviews/sessions/${sessionId}/status`,
      payload,
    ),

  getSessionProgress: (sessionId: number) =>
    api.get<PeerReviewSessionProgressResponse>(`/peer-reviews/sessions/${sessionId}/progress`),

  getResults: (sessionId: number) =>
    api.get<PeerReviewSessionResultsResponse>(`/peer-reviews/sessions/${sessionId}/results`),

  getForm: (token: string) => api.get<PeerReviewFormResponse>(`/peer-reviews/forms/${token}`),

  submitForm: (token: string, payload: PeerReviewFormSubmitRequest) =>
    api.post<MessageResponse, PeerReviewFormSubmitRequest>(`/peer-reviews/forms/${token}/submit`, payload),

  getMySummary: (token: string) =>
    api.get<PeerReviewMySummaryResponse>(`/peer-reviews/forms/${token}/my-summary`),
};

export const tournamentsApi = {
  listSessions: () => api.get<TournamentSessionListResponse>('/tournaments/sessions'),

  createSession: (payload: TournamentSessionCreateRequest) =>
    api.post<TournamentSessionResponse, TournamentSessionCreateRequest>('/tournaments/sessions', payload),

  getSession: (sessionId: number) => api.get<TournamentSessionResponse>(`/tournaments/sessions/${sessionId}`),

  updateSession: (sessionId: number, payload: TournamentSessionUpdateRequest) =>
    api.patch<TournamentSessionResponse, TournamentSessionUpdateRequest>(
      `/tournaments/sessions/${sessionId}`,
      payload,
    ),

  deleteSession: (sessionId: number) => api.delete<MessageResponse>(`/tournaments/sessions/${sessionId}`),

  updateSessionStatus: (sessionId: number, payload: TournamentSessionStatusUpdateRequest) =>
    api.patch<TournamentSessionResponse, TournamentSessionStatusUpdateRequest>(
      `/tournaments/sessions/${sessionId}/status`,
      payload,
    ),

  parseMembersDraft: (payload: TournamentTeamsParseRequest, options?: RequestInit) =>
    api.post<TournamentTeamsParseResponse, TournamentTeamsParseRequest>(
      '/tournaments/members:parse',
      payload,
      options,
    ),

  parseMembers: (sessionId: number, payload: TournamentTeamsParseRequest, options?: RequestInit) =>
    api.post<TournamentTeamsParseResponse, TournamentTeamsParseRequest>(
      `/tournaments/sessions/${sessionId}/members:parse`,
      payload,
      options,
    ),

  confirmMembers: (sessionId: number, payload: TournamentTeamsConfirmRequest) =>
    api.post<TournamentTeamsConfirmResponse, TournamentTeamsConfirmRequest>(
      `/tournaments/sessions/${sessionId}/members:confirm`,
      payload,
    ),

  parseFormat: (sessionId: number, payload: TournamentFormatParseRequest) =>
    api.post<TournamentFormatParseResponse, TournamentFormatParseRequest>(
      `/tournaments/sessions/${sessionId}/format:parse`,
      payload,
    ),

  generateMatches: (sessionId: number) =>
    api.post<TournamentBracketResponse, Record<string, never>>(
      `/tournaments/sessions/${sessionId}/matches:generate`,
      {},
    ),

  getBracket: (sessionId: number) =>
    api.get<TournamentBracketResponse>(`/tournaments/sessions/${sessionId}/bracket`),

  getMatch: (matchId: number) => api.get<TournamentMatchItem>(`/tournaments/matches/${matchId}`),

  getMatchProgress: (matchId: number) =>
    api.get<TournamentMatchProgressResponse>(`/tournaments/matches/${matchId}/progress`),

  updateMatchStatus: (matchId: number, payload: TournamentMatchStatusUpdateRequest) =>
    api.patch<TournamentMatchItem, TournamentMatchStatusUpdateRequest>(
      `/tournaments/matches/${matchId}/status`,
      payload,
    ),

  updateMatchWinner: (matchId: number, payload: TournamentMatchWinnerUpdateRequest) =>
    api.patch<TournamentMatchItem, TournamentMatchWinnerUpdateRequest>(
      `/tournaments/matches/${matchId}/winner`,
      payload,
    ),

  submitVote: (matchId: number, payload: TournamentVoteSubmitRequest) =>
    api.post<TournamentVoteResponse, TournamentVoteSubmitRequest>(
      `/tournaments/matches/${matchId}/vote`,
      payload,
    ),
};

export function createNotificationsSse(onMessage: (event: MessageEvent) => void): EventSource {
  const source = new EventSource(`${API_URL}/notifications/sse`, { withCredentials: true });
  source.addEventListener('notification', onMessage);
  return source;
}

export function createPeerReviewSessionStatusSse(
  onMessage: (payload: PeerReviewSessionStatusSseEvent) => void,
): EventSource {
  const source = new EventSource(`${API_URL}/notification/public/sse`, { withCredentials: true });
  source.addEventListener('peer_review_session_status', (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data || '{}') as PeerReviewSessionStatusSseEvent;
      if (typeof payload.session_id !== 'number' || typeof payload.is_open !== 'boolean') {
        return;
      }
      onMessage(payload);
    } catch {
      // ignore malformed event payload
    }
  });
  return source;
}

export function createPeerReviewProgressSse(
  onMessage: (payload: PeerReviewProgressUpdatedSseEvent) => void,
): EventSource {
  const source = new EventSource(`${API_URL}/notification/public/sse`, { withCredentials: true });
  source.addEventListener('peer_review_progress_updated', (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data || '{}') as PeerReviewProgressUpdatedSseEvent;
      if (typeof payload.session_id !== 'number' || typeof payload.evaluator_user_id !== 'number') {
        return;
      }
      onMessage(payload);
    } catch {
      // ignore malformed event payload
    }
  });
  return source;
}

export function createTournamentMatchStatusSse(
  onMessage: (payload: TournamentMatchStatusSseEvent) => void,
): EventSource {
  const source = new EventSource(`${API_URL}/notification/public/sse`, { withCredentials: true });
  source.addEventListener('tournament_match_status', (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data || '{}') as TournamentMatchStatusSseEvent;
      if (
        typeof payload.match_id !== 'number' ||
        typeof payload.session_id !== 'number' ||
        typeof payload.session_is_open !== 'boolean' ||
        typeof payload.match_status !== 'string'
      ) {
        return;
      }
      onMessage(payload);
    } catch {
      // ignore malformed event payload
    }
  });
  return source;
}

