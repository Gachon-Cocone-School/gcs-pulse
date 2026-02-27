export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function normalizeErrorMessage(value: unknown, fallback: string): string {
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
