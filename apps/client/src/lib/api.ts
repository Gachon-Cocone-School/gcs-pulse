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
  ProfessorOverviewResponse,
  ProfessorRiskEvaluateResponse,
  ProfessorRiskHistoryResponse,
  ProfessorRiskQueueResponse,
} from './types';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api-dev.1000.school';

export { ApiError };

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
    const response = await fetchWithRetry(url, {
      ...options,
      credentials: 'include',
      headers,
    });

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
  } catch (error) {
    if (error instanceof ApiError) {
      // 이미 ApiError로 래핑되어 있으면 그대로 다시 던집니다.
      throw error;
    }

    // 네트워크/환경 오류: ApiError(status=0)를 던져 호출부가 상태를 판별할 수 있게 합니다.
    const networkErrorMessage = 'Network request failed. Please check if the backend server is running.';
    toast.error(networkErrorMessage, {
      id: 'network-error',
    });
    console.error(`API Request Failed: ${method} ${url}`, error);

    // status=0으로 네트워크 오류를 명시
    throw new ApiError(networkErrorMessage, 0);
  }
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiFetch<T>(endpoint, { ...options, method: 'GET' }),

  post: <T, B = any>(endpoint: string, data?: B, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    }),

  put: <T, B = any>(endpoint: string, data?: B, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
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

export const professorApi = {
  overview: () => api.get<ProfessorOverviewResponse>('/professor/overview'),

  riskQueue: (params?: { limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (typeof params?.limit === 'number') searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    const endpoint = query ? `/professor/risk-queue?${query}` : '/professor/risk-queue';
    return api.get<ProfessorRiskQueueResponse>(endpoint);
  },

  riskHistory: (userId: number, params?: { limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (typeof params?.limit === 'number') searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    const endpoint = query
      ? `/professor/students/${userId}/risk-history?${query}`
      : `/professor/students/${userId}/risk-history`;
    return api.get<ProfessorRiskHistoryResponse>(endpoint);
  },

  riskEvaluate: (userId: number) =>
    api.post<ProfessorRiskEvaluateResponse>(`/professor/students/${userId}/risk-evaluate`),
};

export function createNotificationsSse(onMessage: (event: MessageEvent) => void): EventSource {
  const source = new EventSource(`${API_URL}/notifications/sse`, { withCredentials: true });
  source.addEventListener('notification', onMessage);
  return source;
}
