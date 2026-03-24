'use client';

import React from 'react';
import { useAuth } from '@/context/auth-context';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { hasPrivilegedRole } from '@/lib/types';

type ProtectedRouteProps = {
  children: React.ReactNode;
  requirePrivilegedRole?: boolean;
};

export function ProtectedRoute({ children, requirePrivilegedRole = false }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const currentPath = searchParams.toString()
        ? `${pathname}?${searchParams.toString()}`
        : pathname;
      router.replace(`/login?next=${encodeURIComponent(currentPath)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname, searchParams]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="theme-spinner h-12 w-12 rounded-full border-4 animate-spin" />
          <p className="text-muted-foreground font-medium">인증 상태 확인 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requirePrivilegedRole && !hasPrivilegedRole(user?.roles)) {
    return <AccessDeniedView reason="student-only" />;
  }

  return <>{children}</>;
}
