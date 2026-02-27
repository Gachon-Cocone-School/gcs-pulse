import { ApiError } from './apiErrors';
import { fetchWithRetry } from './fetchWithRetry';

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

let csrfTokenCache: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

export function isUnsafeMethod(method: string): boolean {
  return UNSAFE_METHODS.has(method.toUpperCase());
}

export function hasBearerAuthorization(headers: Headers): boolean {
  const authorization = headers.get('Authorization') ?? headers.get('authorization');
  if (!authorization) return false;

  const [scheme, token] = authorization.split(' ', 2);
  return scheme?.toLowerCase() === 'bearer' && Boolean(token?.trim());
}

export async function getCsrfToken(apiUrl: string): Promise<string> {
  if (csrfTokenCache) {
    return csrfTokenCache;
  }

  if (!csrfTokenPromise) {
    csrfTokenPromise = (async () => {
      const response = await fetchWithRetry(`${apiUrl}/auth/csrf`, {
        method: 'GET',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new ApiError('Failed to obtain CSRF token', response.status);
      }

      const data = await response.json().catch(() => ({}));
      const csrfToken = typeof data?.csrf_token === 'string' ? data.csrf_token : '';
      if (!csrfToken) {
        throw new ApiError('Failed to obtain CSRF token', response.status);
      }

      csrfTokenCache = csrfToken;
      return csrfToken;
    })().finally(() => {
      csrfTokenPromise = null;
    });
  }

  return csrfTokenPromise;
}
