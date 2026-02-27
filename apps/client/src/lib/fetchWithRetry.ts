import { ApiError } from './apiErrors';

export async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = 3,
  backoff = 300,
): Promise<Response> {
  const method =
    options && (options as any).method
      ? (options as any).method.toString().toUpperCase()
      : 'GET';

  const idempotentMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
  const shouldRetry = idempotentMethods.has(method);

  try {
    return await fetch(url, options);
  } catch (err: any) {
    const message = err?.message || 'Network request failed';

    if (!shouldRetry || retries <= 1) {
      try {
        console.error(`[fetchWithRetry] network error for ${url}`, err);
      } catch {
        // noop
      }
      throw new ApiError(message, 0);
    }

    await new Promise((resolve) => setTimeout(resolve, backoff));
    return fetchWithRetry(url, options, retries - 1, backoff * 2);
  }
}
