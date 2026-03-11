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
  PeerEvaluationFormResponse,
  PeerEvaluationFormSubmitRequest,
  PeerEvaluationMySummaryResponse,
  PeerEvaluationSessionCreateRequest,
  PeerEvaluationSessionMembersConfirmRequest,
  PeerEvaluationSessionMembersConfirmResponse,
  PeerEvaluationSessionMembersParseRequest,
  PeerEvaluationSessionMembersParseResponse,
  PeerEvaluationSessionListResponse,
  PeerEvaluationSessionProgressResponse,
  PeerEvaluationSessionResponse,
  PeerEvaluationSessionResultsResponse,
  PeerEvaluationSessionStatusUpdateRequest,
  PeerEvaluationSessionUpdateRequest,
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

export const peerEvaluationsApi = {
  listSessions: () => api.get<PeerEvaluationSessionListResponse>('/peer-reviews/sessions'),

  createSession: (payload: PeerEvaluationSessionCreateRequest) =>
    api.post<PeerEvaluationSessionResponse, PeerEvaluationSessionCreateRequest>(
      '/peer-reviews/sessions',
      payload,
    ),

  updateSession: (sessionId: number, payload: PeerEvaluationSessionUpdateRequest) =>
    api.patch<PeerEvaluationSessionResponse, PeerEvaluationSessionUpdateRequest>(
      `/peer-reviews/sessions/${sessionId}`,
      payload,
    ),

  deleteSession: (sessionId: number) =>
    api.delete<{ message: string }>(`/peer-reviews/sessions/${sessionId}`),

  parseMembers: (
    sessionId: number,
    payload: PeerEvaluationSessionMembersParseRequest,
    options?: RequestInit,
  ) =>
    api.post<PeerEvaluationSessionMembersParseResponse, PeerEvaluationSessionMembersParseRequest>(
      `/peer-reviews/sessions/${sessionId}/members:parse`,
      payload,
      options,
    ),

  confirmMembers: (sessionId: number, payload: PeerEvaluationSessionMembersConfirmRequest) =>
    api.post<PeerEvaluationSessionMembersConfirmResponse, PeerEvaluationSessionMembersConfirmRequest>(
      `/peer-reviews/sessions/${sessionId}/members:confirm`,
      payload,
    ),

  getSession: (sessionId: number) => api.get<PeerEvaluationSessionResponse>(`/peer-reviews/sessions/${sessionId}`),

  updateSessionStatus: (sessionId: number, payload: PeerEvaluationSessionStatusUpdateRequest) =>
    api.patch<PeerEvaluationSessionResponse, PeerEvaluationSessionStatusUpdateRequest>(
      `/peer-reviews/sessions/${sessionId}/status`,
      payload,
    ),

  getSessionProgress: (sessionId: number) =>
    api.get<PeerEvaluationSessionProgressResponse>(`/peer-reviews/sessions/${sessionId}/progress`),

  getResults: (sessionId: number) =>
    api.get<PeerEvaluationSessionResultsResponse>(`/peer-reviews/sessions/${sessionId}/results`),

  getForm: (token: string) => api.get<PeerEvaluationFormResponse>(`/peer-reviews/forms/${token}`),

  submitForm: (token: string, payload: PeerEvaluationFormSubmitRequest) =>
    api.post<{ message: string }, PeerEvaluationFormSubmitRequest>(
      `/peer-reviews/forms/${token}/submit`,
      payload,
    ),

  getMySummary: (token: string) =>
    api.get<PeerEvaluationMySummaryResponse>(`/peer-reviews/forms/${token}/my-summary`),
};

export function createNotificationsSse(onMessage: (event: MessageEvent) => void): EventSource {
  const source = new EventSource(`${API_URL}/notifications/sse`, { withCredentials: true });
  source.addEventListener('notification', onMessage);
  return source;
}
