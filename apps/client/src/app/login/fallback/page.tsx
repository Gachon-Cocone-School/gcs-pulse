import { Suspense } from 'react';
import FallbackLoginPageClient from './FallbackLoginPageClient';

export const metadata = { title: '간편 입장' };

export default function FallbackLoginPage() {
  return (
    <Suspense>
      <FallbackLoginPageClient />
    </Suspense>
  );
}
