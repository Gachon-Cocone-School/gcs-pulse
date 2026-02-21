import { toast } from 'sonner';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api-dev.1000.school';

export class ApiError extends Error {
  status: number;
  
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// /Users/hexa/projects/temp/gcs-mono/apps/client/src/lib/api.ts
// 기존 재시도 헬퍼를 더 명확한 네트워크 에러 래핑으로 교체
async function fetchWithRetry(url: string, options: RequestInit, retries = 3, backoff = 300) {
  // Determine HTTP method; default to GET
  const method = (options && (options as any).method ? (options as any).method : 'GET').toString().toUpperCase();
  // Only retry safe/idempotent methods. Avoid retrying non-idempotent methods (POST, PATCH, etc.) to prevent duplicate side-effects.
  const idempotentMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
  const shouldRetry = idempotentMethods.has(method);

  try {
    return await fetch(url, options);
  } catch (err: any) {
    const message = err?.message || 'Network request failed';

    // If the method is not considered safe to retry, or we've exhausted retries, wrap and throw as ApiError(status=0)
    if (!shouldRetry || retries <= 1) {
      // Temporary logging to help debug network failures during development/CI
      try {
        // Use console.error so it's visible in CI logs
        console.error(`[fetchWithRetry] network error for ${url}`, err);
      } catch (loggingErr) {
        // swallow logging errors to avoid masking the original network error
      }

      throw new ApiError(message, 0);
    }

    await new Promise((r) => setTimeout(r, backoff));
    return fetchWithRetry(url, options, retries - 1, backoff * 2);
  }
}

function normalizeErrorMessage(value: unknown, fallback: string): string {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed || fallback;
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;

    if (typeof record.message === 'string' && record.message.trim()) {
      return record.message.trim();
    }

    try {
      const serialized = JSON.stringify(value);
      if (serialized && serialized !== '{}') {
        return serialized;
      }
    } catch {
      // noop
    }
  }

  if (value == null) {
    return fallback;
  }

  const text = String(value).trim();
  return text || fallback;
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const method = options.method || 'GET';

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

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
