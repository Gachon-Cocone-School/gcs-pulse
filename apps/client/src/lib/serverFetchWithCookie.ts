import { headers } from 'next/headers';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchWithCookie<T>(endpoint: string): Promise<T | null> {
  const headerStore = await headers();
  const cookieHeader = headerStore.get('cookie') ?? '';

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}
