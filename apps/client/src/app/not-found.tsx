'use client';

import { ErrorView } from '@/components/views/ErrorView';

export default function NotFound() {
  return (
    <ErrorView
      code={404}
      title="페이지를 찾을 수 없습니다"
      message="요청하신 페이지가 존재하지 않거나, 이동되었을 수 있습니다. 입력하신 주소가 정확한지 확인해 주세요."
    />
  );
}
