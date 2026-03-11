import { toast } from 'sonner';

import { ApiError, normalizeErrorMessage } from './apiErrors';
import { fetchWithRetry } from './fetchWithRetry';
import { getCsrfToken, hasBearerAuthorization, isUnsafeMethod } from './csrf';
import type {
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
  const method = (options.method || 'GET').toUpperCase();
  const response = await requestWithCommonOptions(endpoint, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const fallbackMessage = `Error ${response.status}: ${response.statusText}`;
    const errorMessage = normalizeErrorMessage(errorData.detail ?? errorData.message, fallbackMessage);

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
        description: `${method} ${endpoint} (${response.status})`,
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
    api.delete<{ message: string }>(`/peer-reviews/sessions/${sessionId}`),

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
    api.post<{ message: string }, PeerReviewFormSubmitRequest>(
      `/peer-reviews/forms/${token}/submit`,
      payload,
    ),

  getMySummary: (token: string) =>
    api.get<PeerReviewMySummaryResponse>(`/peer-reviews/forms/${token}/my-summary`),
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

