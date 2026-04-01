'use client';

import { useEffect } from 'react';

/**
 * 배포 후 청크 해시가 변경됐을 때 ChunkLoadError가 발생하면
 * 페이지를 자동 새로고침해서 최신 청크를 받아오도록 복구합니다.
 * 무한 루프 방지를 위해 한 번만 새로고침합니다.
 */
export function ChunkErrorHandler() {
  useEffect(() => {
    const handler = (event: PromiseRejectionEvent) => {
      const error = event.reason;
      if (error?.name === 'ChunkLoadError') {
        const reloadKey = 'chunk_error_reload';
        if (!sessionStorage.getItem(reloadKey)) {
          sessionStorage.setItem(reloadKey, '1');
          window.location.reload();
        }
      }
    };

    window.addEventListener('unhandledrejection', handler);
    return () => window.removeEventListener('unhandledrejection', handler);
  }, []);

  return null;
}
