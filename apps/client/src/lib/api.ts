import { toast } from 'sonner';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Simple retry helper
async function fetchWithRetry(url: string, options: RequestInit, retries = 3, backoff = 300) {
  try {
    return await fetch(url, options);
  } catch (err) {
    if (retries <= 1) throw err;
    await new Promise(r => setTimeout(r, backoff));
    return fetchWithRetry(url, options, retries - 1, backoff * 2);
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
      const errorMessage = errorData.detail || errorData.message || `Error ${response.status}: ${response.statusText}`;

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
      throw error;
    }
    const networkErrorMessage = 'Network request failed. Please check if the backend server is running.';
    toast.error(networkErrorMessage, {
      id: 'network-error',
    });
    console.error(`API Request Failed: ${method} ${url}`, error);
    throw new Error(networkErrorMessage);
  }
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) => 
    apiFetch<T>(endpoint, { ...options, method: 'GET' }),
  
  post: <T>(endpoint: string, data?: any, options?: RequestInit) => 
    apiFetch<T>(endpoint, { 
      ...options, 
      method: 'POST', 
      body: data ? JSON.stringify(data) : undefined 
    }),
  
  put: <T>(endpoint: string, data?: any, options?: RequestInit) => 
    apiFetch<T>(endpoint, { 
      ...options, 
      method: 'PUT', 
      body: data ? JSON.stringify(data) : undefined 
    }),
  
  delete: <T>(endpoint: string, options?: RequestInit) => 
    apiFetch<T>(endpoint, { ...options, method: 'DELETE' }),
};
