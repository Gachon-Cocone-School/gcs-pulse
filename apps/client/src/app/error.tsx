'use client';

import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';
import { ErrorView } from '@/components/views/ErrorView';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <ErrorView
      code={500}
      title="예기치 못한 오류가 발생했습니다"
      message="시스템 내부 오류로 인해 페이지를 표시할 수 없습니다. 잠시 후 다시 시도해 주세요."
      onRetry={() => reset()}
    />
  );
}
